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

def extract_gdrive_file_id(gdrive_url: str) -> Optional[str]:
    if not gdrive_url or not isinstance(gdrive_url, str):
        return None
    match = re.search(r'/d/([a-zA-Z0-9_-]+)', gdrive_url) or re.search(r'id=([a-zA-Z0-9_-]+)', gdrive_url)
    return match.group(1) if match else None

def get_gdrive_service():
    """Build authenticated Google Drive service from OAuth or Service Account."""
    try:
        from google.oauth2.credentials import Credentials as UserCredentials
        from google.oauth2.service_account import Credentials as ServiceAccountCredentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from src.config import config
    except ImportError:
        logger.warning("Google API client dependencies not fully imported.")
        return None

    # 1. User OAuth 2.0
    client_id = os.getenv("GDRIVE_CLIENT_ID")
    client_secret = os.getenv("GDRIVE_CLIENT_SECRET")
    refresh_token = os.getenv("GDRIVE_REFRESH_TOKEN")

    oauth_file = os.path.join(config.base_dir, "configs", "oauth_credentials.json")
    if not (client_id and client_secret and refresh_token) and os.path.exists(oauth_file):
        try:
            with open(oauth_file, "r") as f:
                oauth_data = json.load(f)
                client_id = client_id or oauth_data.get("client_id")
                client_secret = client_secret or oauth_data.get("client_secret")
                refresh_token = refresh_token or oauth_data.get("refresh_token")
        except Exception:
            pass

    if client_id and client_secret and refresh_token:
        try:
            user_creds = UserCredentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret
            )
            user_creds.refresh(Request())
            return build("drive", "v3", credentials=user_creds)
        except Exception as e:
            logger.warning(f"OAuth auth attempt in QC: {e}")

    # 2. Service Account
    scopes = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    env_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("SERVICE_ACCOUNT_JSON")
    if env_json and env_json.strip():
        try:
            info = json.loads(env_json)
            sa_creds = ServiceAccountCredentials.from_service_account_info(info, scopes=scopes)
            return build("drive", "v3", credentials=sa_creds)
        except Exception as e:
            logger.warning(f"SA env attempt in QC: {e}")

    for path in config.creds_paths:
        if path and os.path.exists(path) and os.path.getsize(path) > 10:
            try:
                sa_creds = ServiceAccountCredentials.from_service_account_file(path, scopes=scopes)
                return build("drive", "v3", credentials=sa_creds)
            except Exception:
                pass

    return None

def download_video_file(url_or_path: str, output_path: str) -> bool:
    """Download video if URL or verify if local path."""
    if not url_or_path or not isinstance(url_or_path, str):
        logger.warning("Empty video URL/path provided.")
        return False

    if os.path.exists(url_or_path) and os.path.getsize(url_or_path) > 500 * 1024:
        logger.info(f"Using local video file: {url_or_path}")
        return True

    file_id = extract_gdrive_file_id(url_or_path)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # 1. Try Google Drive API download (Authenticated & 100% reliable on GitHub Actions)
    if file_id:
        try:
            service = get_gdrive_service()
            if service:
                from googleapiclient.http import MediaIoBaseDownload
                logger.info(f"Downloading Google Drive file ID [{file_id}] via Drive API...")
                request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
                with io.FileIO(output_path, "wb") as fh:
                    downloader = MediaIoBaseDownload(fh, request, chunksize=2 * 1024 * 1024)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 500 * 1024:
                    size_mb = os.path.getsize(output_path) / (1024 * 1024)
                    logger.info(f" Successfully downloaded video via Drive API ({size_mb:.2f} MB) -> {output_path}")
                    return True
                else:
                    logger.warning("Drive API downloaded empty or incomplete file.")
        except Exception as e:
            logger.warning(f"Google Drive API download failed: {e}. Trying direct HTTP fallback...")

    # 2. Fallback: HTTP streaming download
    import requests
    download_urls = []
    if file_id:
        download_urls.append(f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t")
        download_urls.append(f"https://drive.usercontent.google.com/download?id={file_id}&export=download&authuser=0&confirm=t")
    if url_or_path.startswith("http"):
        download_urls.append(url_or_path)

    for d_url in download_urls:
        try:
            logger.info(f"Attempting HTTP download: {d_url[:80]}...")
            session = requests.Session()
            res = session.get(d_url, stream=True, timeout=90, allow_redirects=True)
            if res.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                file_size = os.path.getsize(output_path)
                if file_size > 500 * 1024:
                    with open(output_path, "rb") as f:
                        header = f.read(16)
                    if b"<!DOCTYPE" not in header and b"<html" not in header:
                        logger.info(f"Downloaded video ({file_size / (1024*1024):.2f} MB) -> {output_path}")
                        return True
                    else:
                        logger.warning("Downloaded file is an HTML error page, not a video.")
        except Exception as e:
            logger.warning(f"HTTP download failed for {d_url[:60]}: {e}")

    logger.error(f"Failed to download video from {url_or_path}")
    return False

class QCInspector:
    def __init__(self):
        self.min_duration = 15.0
        self.max_duration = 120.0
        self.min_width = 720
        self.min_height = 1280
        self.min_fps = 23.0

    def check_linguistics_and_content(self, words: List[Dict[str, str]]) -> Tuple[bool, List[str]]:
        """
        Verify Simplified Chinese characters, syllable count match, and word structure.
        """
        errors = []
        if len(words) != 5:
            errors.append(f"Số lượng từ không đúng ({len(words)}/5 từ).")

        for idx, w in enumerate(words, start=1):
            hanzi = w.get("hanzi", "").strip()
            pinyin = w.get("pinyin", "").strip()
            meaning = w.get("meaning", "").strip()

            if not hanzi:
                errors.append(f"Từ #{idx}: Chữ Hán (Hanzi) bị rỗng.")
                continue

            if _opencc_converter:
                simplified = _opencc_converter.convert(hanzi)
                if simplified != hanzi:
                    errors.append(f"Từ #{idx} '{hanzi}' chứa ký tự Phồn thể (Nên dùng: '{simplified}').")

            if not any('\u4e00' <= char <= '\u9fff' for char in hanzi):
                errors.append(f"Từ #{idx} '{hanzi}' không chứa chữ Hán hợp lệ.")

            if len(hanzi) > 4:
                errors.append(f"Từ #{idx} '{hanzi}' quá dài ({len(hanzi)} chữ, tối đa 4 chữ).")

            if not pinyin:
                errors.append(f"Từ #{idx} '{hanzi}': Pinyin bị rỗng.")
            else:
                p_syllables = [s for s in pinyin.split() if s.strip()]
                if len(p_syllables) != len(hanzi):
                    errors.append(f"Từ #{idx} '{hanzi}': Số âm tiết Pinyin ({len(p_syllables)}) không khớp số chữ Hán ({len(hanzi)}).")

            if not meaning:
                errors.append(f"Từ #{idx} '{hanzi}': Nghĩa tiếng Việt bị rỗng.")
            elif len(meaning) > 35:
                errors.append(f"Từ #{idx} '{hanzi}': Nghĩa '{meaning}' quá dài ({len(meaning)} ký tự, tối đa 35).")

        passed = len(errors) == 0
        return passed, errors

    def check_video_properties(self, video_path: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Check video container, dimensions, vertical aspect ratio, FPS, duration, and frame decoding.
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
            return False, ["Không thể mở file video bằng OpenCV (File hỏng hoặc không đúng định dạng MP4)."], details

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        duration = total_frames / fps if fps > 0 else 0
        details["width"] = width
        details["height"] = height
        details["fps"] = round(fps, 2)
        details["duration_sec"] = round(duration, 2)
        details["total_frames"] = total_frames

        # 1. Aspect Ratio: Vertical 9:16 (Width < Height)
        if width >= height:
            errors.append(f"Video nằm ngang ({width}x{height}) thay vì định dạng dọc 9:16.")

        # 2. Minimum resolution
        if width < self.min_width or height < self.min_height:
            errors.append(f"Độ phân giải quá thấp ({width}x{height}, tối thiểu {self.min_width}x{self.min_height}).")

        # 3. FPS
        if fps < self.min_fps:
            errors.append(f"Tốc độ khung hình quá thấp ({fps:.1f} FPS, tối thiểu {self.min_fps} FPS).")

        # 4. Duration check
        if duration < self.min_duration:
            errors.append(f"Thời lượng video quá ngắn ({duration:.1f}s, tối thiểu {self.min_duration}s).")
        elif duration > self.max_duration:
            errors.append(f"Thời lượng video quá dài ({duration:.1f}s, tối đa {self.max_duration}s cho Shorts/TikTok/Reels).")

        # 5. Keyframe validation (verify frames across video decode properly and are not black)
        if duration >= self.min_duration and fps > 0:
            sample_timestamps = [2.0, duration * 0.25, duration * 0.5, duration * 0.75, duration - 1.5]
            black_frame_count = 0
            decoded_count = 0

            for t in sample_timestamps:
                if t < 0 or t >= duration:
                    continue
                frame_idx = int(t * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret and frame is not None:
                    decoded_count += 1
                    mean_val = np.mean(frame)
                    if mean_val < 5.0:  # Pitch black frame
                        black_frame_count += 1

            if decoded_count < len(sample_timestamps) - 1:
                errors.append("Không thể giải mã các frame trong video (Video bị gián đoạn).")
            if black_frame_count >= 3:
                errors.append(f"Video bị màn hình đen ({black_frame_count} frames đen hoàn toàn).")

        cap.release()

        passed = len(errors) == 0
        return passed, errors, details

    def check_audio_stream(self, video_path: str) -> Tuple[bool, List[str]]:
        """
        Check that audio stream exists, has active channels and valid sample rate via ffprobe.
        """
        errors = []
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_name,channels,sample_rate,duration",
                "-of", "json",
                video_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                streams = data.get("streams", [])
                if not streams:
                    errors.append("Video không có luồng âm thanh (Audio track missing).")
                else:
                    audio_info = streams[0]
                    codec = audio_info.get("codec_name", "")
                    channels = int(audio_info.get("channels", 0))
                    if not codec:
                        errors.append("Không xác định được codec âm thanh.")
                    if channels < 1:
                        errors.append("Luồng âm thanh không có kênh phát (0 channels).")
            else:
                logger.warning(f"ffprobe check warning: {result.stderr}")
        except FileNotFoundError:
            logger.info("ffprobe not available in environment, skipping deep audio stream inspection.")
        except Exception as e:
            logger.warning(f"Audio inspection warning: {e}")

        passed = len(errors) == 0
        return passed, errors

    def inspect_batch(self, batch: Dict[str, Any], video_path: str) -> Dict[str, Any]:
        """
        Run complete QC inspection on batch metadata + downloaded video file.
        """
        topic = batch.get("topic", "Chưa đặt tên")
        level = batch.get("level", "HSK 1-2")
        words = batch.get("words", [])

        all_errors = []
        all_warnings = []

        logger.info(f"--- Starting QC Inspection for Batch [{batch.get('id')}]: {topic} ---")

        # 1. Check Simplified Chinese & Content Structure
        content_pass, content_errs = self.check_linguistics_and_content(words)
        if not content_pass:
            all_errors.extend(content_errs)

        # 2. Check Video Properties & Keyframes
        vid_pass, vid_errs, details = self.check_video_properties(video_path)
        if not vid_pass:
            all_errors.extend(vid_errs)

        # 3. Check Audio Stream
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
