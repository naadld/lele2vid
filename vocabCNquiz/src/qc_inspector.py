import os
import re
import io
import cv2
import json
import logging
import subprocess
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("QCInspector")

try:
    import opencc
    _opencc_converter = opencc.OpenCC('t2s')
except ImportError:
    _opencc_converter = None

def sanitize_filename(name: str) -> str:
    return re.sub(r'[/\\:*?"<>|]', '_', name).strip()

class QCInspector:
    """Automated Audio-Visual Quality Control Inspector for VocabVNQuiz."""

    def __init__(self, gsheet_mgr=None):
        self.gsheet_mgr = gsheet_mgr

    def inspect_video(self, video_path: str, expected_words: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = {
            "passed": False,
            "errors": [],
            "warnings": [],
            "video_duration": 0,
            "has_audio": False,
            "resolution": "",
            "fps": 0
        }

        if not os.path.exists(video_path):
            results["errors"].append(f"Video file not found: {video_path}")
            return results

        # 1. Check video resolution and FPS via OpenCV
        try:
            cap = cv2.VideoCapture(video_path)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            cap.release()

            results["video_duration"] = round(duration, 2)
            results["resolution"] = f"{width}x{height}"
            results["fps"] = round(fps, 1)

            if width != 1080 or height != 1920:
                results["errors"].append(f"Invalid video resolution: {width}x{height} (Expected: 1080x1920 9:16 vertical).")

            if duration < 30 or duration > 90:
                results["warnings"].append(f"Unusual video duration: {duration:.1f}s (Expected: 45-65s for 5 words).")

        except Exception as e:
            results["errors"].append(f"Error inspecting video stream: {e}")

        # 2. Check audio stream via FFprobe
        try:
            cmd = [
                "ffprobe", "-v", "error", "-show_entries",
                "stream=codec_type", "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            streams = res.stdout.strip().split("\n")
            if "audio" in streams:
                results["has_audio"] = True
            else:
                results["errors"].append("Missing audio stream in rendered video.")
        except Exception as e:
            results["warnings"].append(f"Could not verify audio stream via ffprobe: {e}")

        results["passed"] = len(results["errors"]) == 0
        return results
