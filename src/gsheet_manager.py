import os
import json
import logging
from typing import List, Dict, Any, Optional
import gspread
from google.oauth2.service_account import Credentials
from src.config import config

logger = logging.getLogger("GSheetManager")

STANDARD_COLUMNS = [
    "#",
    "Topic",
    "Level",
    "Status",
    "Word 1",
    "Word 2",
    "Word 3",
    "Word 4",
    "Word 5",
    "Video File",
    "GDrive Link",
    "Created At",
    "Notes"
]

class GSheetManager:
    def __init__(self, credentials_path: str = None, spreadsheet_id: str = None, tab_name: str = None):
        self.spreadsheet_id = spreadsheet_id or config.spreadsheet_id
        self.tab_name = tab_name or config.sheet_tab_name
        self.credentials_path = credentials_path
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        self._authenticate()

    def _get_credentials(self) -> Credentials:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # 1. Try env variable JSON content
        env_json = os.getenv("GCP_SERVICE_ACCOUNT_JSON") or os.getenv("SERVICE_ACCOUNT_JSON")
        if env_json and env_json.strip():
            try:
                info = json.loads(env_json)
                logger.info("Loaded credentials directly from GCP_SERVICE_ACCOUNT_JSON environment variable.")
                return Credentials.from_service_account_info(info, scopes=scopes)
            except Exception as e:
                logger.warning(f"Failed to parse credentials from env JSON: {e}")

        # 2. Try credentials path or fallback paths
        search_paths = [self.credentials_path] if self.credentials_path else []
        search_paths.extend(config.creds_paths)
        
        for path in search_paths:
            if path and os.path.exists(path) and os.path.getsize(path) > 10:
                logger.info(f"Loaded credentials from file: {path}")
                return Credentials.from_service_account_file(path, scopes=scopes)
                
        raise FileNotFoundError(f"No valid Google service account credentials found! Checked: {search_paths}")

    def _authenticate(self):
        credentials = self._get_credentials()
        self.client = gspread.authorize(credentials)
        self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
        
        try:
            self.worksheet = self.spreadsheet.worksheet(self.tab_name)
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Worksheet '{self.tab_name}' not found. Creating it...")
            self.worksheet = self.spreadsheet.add_worksheet(title=self.tab_name, rows=100, cols=20)
            self.init_header()

    def init_header(self):
        """Set up standard column headers in row 1."""
        self.worksheet.update("A1:M1", [STANDARD_COLUMNS])
        logger.info(f"Initialized headers on tab '{self.tab_name}'")

    def get_all_rows(self) -> List[Dict[str, Any]]:
        """Fetch all rows as dictionaries."""
        return self.worksheet.get_all_records()

    def get_pending_batches(self) -> List[Dict[str, Any]]:
        """Retrieve rows with Status == 'Pending'."""
        rows = self.worksheet.get_all_values()
        if not rows or len(rows) < 2:
            return []

        headers = rows[0]
        pending_batches = []

        for row_idx, row in enumerate(rows[1:], start=2):
            row_dict = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            status = row_dict.get("Status", "").strip().lower()
            if status == "pending":
                words = []
                for w_idx in range(1, 6):
                    w_key = f"Word {w_idx}"
                    w_val = row_dict.get(w_key, "").strip()
                    if w_val:
                        parts = [p.strip() for p in w_val.split("|")]
                        hanzi = parts[0]
                        pinyin = parts[1] if len(parts) > 1 else ""
                        hidden = parts[2] if len(parts) > 2 else ""
                        meaning = parts[3] if len(parts) > 3 else ""
                        words.append({
                            "hanzi": hanzi,
                            "pinyin": pinyin,
                            "hidden_pinyin": hidden,
                            "meaning": meaning or hanzi
                        })

                pending_batches.append({
                    "row_index": row_idx,
                    "id": row_dict.get("#", str(row_idx)),
                    "topic": row_dict.get("Topic", "HSK 1-2 • TỪ VỰNG CƠ BẢN"),
                    "level": row_dict.get("Level", "HSK 1-2"),
                    "words": words,
                    "raw_data": row_dict
                })

        return pending_batches

    def update_batch_status(self, row_index: int, status: str, video_file: str = "", gdrive_link: str = ""):
        """Update batch status, video filename and drive link."""
        try:
            self.worksheet.update_cell(row_index, 4, status)
            if video_file:
                self.worksheet.update_cell(row_index, 10, video_file)
            if gdrive_link:
                self.worksheet.update_cell(row_index, 11, gdrive_link)
            logger.info(f"Updated row {row_index} status -> {status}")
        except Exception as e:
            logger.error(f"Failed to update row {row_index}: {e}")

if __name__ == "__main__":
    manager = GSheetManager()
    batches = manager.get_pending_batches()
    print(f"Found {len(batches)} pending batches.")
