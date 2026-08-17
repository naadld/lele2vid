import os
import logging
from typing import Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from src.config import config

logger = logging.getLogger("GDriveUploader")

TARGET_FOLDER_ID = "1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB"

class GDriveUploader:
    def __init__(self, credentials_path: str = None, folder_id: str = TARGET_FOLDER_ID):
        self.credentials_path = credentials_path or self._find_valid_creds()
        self.folder_id = folder_id
        self.service = None
        self._authenticate()

    def _find_valid_creds(self) -> str:
        for path in config.creds_paths:
            if os.path.exists(path) and os.path.getsize(path) > 10:
                return path
        raise FileNotFoundError("No valid Google service account credentials found for GDrive!")

    def _authenticate(self):
        scopes = [
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file"
        ]
        creds = Credentials.from_service_account_file(self.credentials_path, scopes=scopes)
        self.service = build("drive", "v3", credentials=creds)
        logger.info(f"GDriveUploader authenticated with {self.credentials_path}")

    def upload_file(self, file_path: str, custom_filename: Optional[str] = None) -> Optional[str]:
        """
        Uploads a video file to Google Drive folder and returns the web view link.
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found for upload: {file_path}")
            return None

        filename = custom_filename or os.path.basename(file_path)
        logger.info(f"Uploading '{filename}' to Google Drive folder [{self.folder_id}]...")

        file_metadata = {
            "name": filename,
            "parents": [self.folder_id]
        }
        media = MediaFileUpload(file_path, mimetype="video/mp4", resumable=True)

        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, name, webViewLink, webContentLink",
                supportsAllDrives=True
            ).execute()

            file_id = file.get("id")
            web_link = file.get("webViewLink")
            logger.info(f"Upload successful! File ID: {file_id}, Link: {web_link}")

            # Try to grant read permission so anyone with link can view
            try:
                self.service.permissions().create(
                    fileId=file_id,
                    body={"type": "anyone", "role": "reader"},
                    supportsAllDrives=True
                ).execute()
            except Exception as pe:
                logger.warning(f"Could not set public permission: {pe}")

            return web_link
        except Exception as e:
            logger.error(f"Failed to upload to Google Drive: {e}")
            return None

if __name__ == "__main__":
    uploader = GDriveUploader()
    test_video = "/media/vpsg16gb/Workspace/lelehoctiengtrung_pinyin/output/videos/tiktok_pinyin_hsk_master_1080p.mp4"
    if os.path.exists(test_video):
        link = uploader.upload_file(test_video, "#1.HSK 1 • Đồ Ăn & Thức Uống.mp4")
        print("Upload Result:", link)
