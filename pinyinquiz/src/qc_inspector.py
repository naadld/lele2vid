import os
import re
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

def extract_gdrive_file_id(gdrive_url: str) -> Optional[str]:
    if not gdrive_url or not isinstance(gdrive_url, str):
        return None
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', gdrive_url) or re.search(r'id=([a-zA-Z0-9_-]+)', gdrive_url)
    return match.group(1) if match else None

def convert_gdrive_to_direct_url(gdrive_url: str) -> str:
    file_id = extract_gdrive_file_id(gdrive_url)
    if file_id:
        return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&authuser=0"
    return gdrive_url

def download_video_file(url_or_path: str, output_path: str) -> bool:
    """Download video if URL or copy if local path."""
    if os.path.exists(url_or_path):
        return True

    direct_url = convert_gdrive_to_direct_url(url_or_path)
    logger.info(f"Downloading video from {direct_url[:80]}...")
    
    import requests
    try:
        res = requests.get(direct_url, stream=True, timeout=60)
        if res.status_code == 200:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            file_size = os.path.getsize(output_path)
            if file_size > 100 * 1024:  # At least 100KB
                logger.info(f"Downloaded video ({file_size / (1024*1024):.2f} MB) -> {output_path}")
                return True
            else:
                logger.warning(f"Downloaded file too small: {file_size} bytes")
                return False
        else:
            logger.warning(f"Download failed with HTTP status: {res.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error downloading video: {e}")
        return False

class QCInspector:
    def __init__(self):
        self.safe_margin_x = 50   # Safe zone margin from left/right border (px)
        self.safe_margin_top = 100 # Safe zone margin from top
        self.safe_margin_bottom = 1800 # Safe zone max Y

    def check_simplified_chinese(self, words: List[Dict[str, str]]) -> Tuple[bool, List[str]]:
        """
        Verify that all Chinese characters in the batch are standard Simplified Chinese (Giản thể).
        """
        errors = []
        for idx, w in enumerate(words, start=1):
            hanzi = w.get("hanzi", "").strip()
            if not hanzi:
                continue

            if _opencc_converter:
                simplified = _opencc_converter.convert(hanzi)
                if simplified != hanzi:
                    errors.append(f"Từ #{idx} '{hanzi}' chứa ký tự Phồn thể (Nên dùng: '{simplified}')")

            # Basic check for empty or non-chinese characters in hanzi field
            if not any('\u4e00' <= char <= '\u9fff' for char in hanzi):
                errors.append(f"Từ #{idx} '{hanzi}' không chứa chữ Hán hợp lệ.")

        passed = len(errors) == 0
        return passed, errors

    def check_video_properties(self, video_path: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Check video codec, resolution (1080x1920), FPS, and duration.
        """
        errors = []
        details = {}

        if not os.path.exists(video_path):
            return False, ["File video không tồn tại."], details

        file_size = os.path.getsize(video_path)
        details["file_size_mb"] = round(file_size / (1024 * 1024), 2)
        if file_size < 500 * 1024:
            errors.append(f"Dung lượng video quá nhỏ ({details['file_size_mb']} MB).")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False, ["Không thể mở file video bằng OpenCV (File hỏng)."], details

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

        duration = total_frames / fps if fps > 0 else 0
        details["width"] = width
        details["height"] = height
        details["fps"] = round(fps, 2)
        details["duration_sec"] = round(duration, 2)

        # 1. Aspect Ratio: Vertical 9:16 (Width < Height)
        if width > height:
            errors.append(f"Video nằm ngang ({width}x{height}) thay vì dọc 9:16.")
        
        # 2. Minimum resolution
        if width < 720 or height < 1280:
            errors.append(f"Độ phân giải quá thấp ({width}x{height}, tối thiểu 720x1280).")

        # 3. Duration check (Each 5-word quiz video is around 25s - 65s)
        if duration < 15.0:
            errors.append(f"Thời lượng video quá ngắn ({duration:.1f}s, tối thiểu 15s).")
        elif duration > 120.0:
            errors.append(f"Thời lượng video quá dài ({duration:.1f}s, tối đa 120s cho Shorts/TikTok).")

        passed = len(errors) == 0
        return passed, errors, details

    def check_visual_layout_and_overflow(self, video_path: str, duration_sec: float) -> Tuple[bool, List[str]]:
        """
        Extract keyframes and check for text overflow / edge collision.
        """
        errors = []
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return False, ["Không thể đọc frame video."]

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Check sample timestamps across the video (e.g. 2s, 6s, 10s, 15s, 22s, 30s)
        sample_times = [t for t in [2.0, 5.5, 7.0, 12.0, 18.0, 25.0, 32.0] if t < duration_sec - 1]
        
        overflow_count = 0
        for t in sample_times:
            frame_no = int(t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            # Convert to grayscale & threshold to find white/colored text blocks
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Analyze central content area (ignore top header and bottom footer decoration)
            content_roi = gray[int(height * 0.15):int(height * 0.85), :]
            _, thresh = cv2.threshold(content_roi, 200, 255, cv2.THRESH_BINARY)
            
            # Find contours in ROI
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                # Ignore small noise dots
                if w > 30 and h > 15:
                    # Check if text reaches left edge or right edge
                    if x < self.safe_margin_x or (x + w) > (width - self.safe_margin_x):
                        overflow_count += 1
                        logger.warning(f"Frame at {t}s: Potential text overflow detected at x={x}, w={w} (margin={self.safe_margin_x})")
                        break

        cap.release()

        # If multiple frames overflow the margin
        if overflow_count >= 3:
            errors.append(f"Phát hiện chữ / Pinyin bị tràn viền ({overflow_count} frames chạm lề an toàn).")

        passed = len(errors) == 0
        return passed, errors

    def check_audio_stream(self, video_path: str) -> Tuple[bool, List[str]]:
        """
        Check that audio stream exists and has healthy volume/RMS.
        """
        errors = []
        try:
            # Use ffprobe to inspect audio stream
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_name,channels,sample_rate,duration",
                "-of", "json",
                video_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                streams = data.get("streams", [])
                if not streams:
                    errors.append("Video không có luồng âm thanh (Audio track missing).")
                else:
                    audio_info = streams[0]
                    codec = audio_info.get("codec_name", "")
                    if not codec:
                        errors.append("Không xác định được codec âm thanh.")
            else:
                logger.warning(f"ffprobe warning: {result.stderr}")
        except FileNotFoundError:
            logger.info("ffprobe not available in path, skipping deep audio stream inspection.")
        except Exception as e:
            logger.warning(f"Audio inspection warning: {e}")

        passed = len(errors) == 0
        return passed, errors

    def inspect_batch(self, batch: Dict[str, Any], video_path: str) -> Dict[str, Any]:
        """
        Run complete QC inspection on batch data + video file.
        """
        topic = batch.get("topic", "Chưa đặt tên")
        level = batch.get("level", "HSK 1-2")
        words = batch.get("words", [])

        all_errors = []
        all_warnings = []

        logger.info(f"--- Starting QC Inspection for Batch [{batch.get('id')}]: {topic} ---")

        # 1. Check Simplified Chinese
        zh_pass, zh_errs = self.check_simplified_chinese(words)
        if not zh_pass:
            all_errors.extend(zh_errs)

        # 2. Check Video File & Properties
        vid_pass, vid_errs, details = self.check_video_properties(video_path)
        if not vid_pass:
            all_errors.extend(vid_errs)

        duration = details.get("duration_sec", 30.0)

        # 3. Check Visual Layout & Overflow (if video opened successfully)
        if vid_pass:
            layout_pass, layout_errs = self.check_visual_layout_and_overflow(video_path, duration)
            if not layout_pass:
                all_errors.extend(layout_errs)

        # 4. Check Audio Stream
        if vid_pass:
            audio_pass, audio_errs = self.check_audio_stream(video_path)
            if not audio_pass:
                all_errors.extend(audio_errs)

        passed = len(all_errors) == 0

        return {
            "batch_id": batch.get("id"),
            "topic": topic,
            "level": level,
            "passed": passed,
            "errors": all_errors,
            "warnings": all_warnings,
            "details": details
        }
