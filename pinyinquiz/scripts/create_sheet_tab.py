import os
import sys
import json
import logging
import gspread
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CreateSheetTab")

SPREADSHEET_ID = "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0"
SHEET_TAB_NAME = "pinyin"

POSSIBLE_CREDS_PATHS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "service_account.json"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "configs", "service_account.json"),
    "/media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz/configs/service_account.json",
    os.path.expanduser("~/.config/gspread/service_account.json"),
    "configs/service_account.json"
]

def get_gspread_client():
    for p in POSSIBLE_CREDS_PATHS:
        if os.path.exists(p):
            logger.info(f"Using credentials from {p}")
            try:
                with open(p, "r") as f:
                    data = json.load(f)
                if "private_key" in data:
                    return gspread.service_account(filename=p)
            except Exception as e:
                logger.warning(f"Failed to load {p}: {e}")
    raise FileNotFoundError("No valid Google service account credentials found!")

def init_pinyin_tab():
    gc = get_gspread_client()
    logger.info(f"Opening spreadsheet {SPREADSHEET_ID}...")
    sh = gc.open_by_key(SPREADSHEET_ID)
    
    # Check if tab already exists
    existing_tabs = [ws.title for ws in sh.worksheets()]
    logger.info(f"Existing tabs: {existing_tabs}")
    
    if SHEET_TAB_NAME in existing_tabs:
        logger.info(f"Worksheet tab '{SHEET_TAB_NAME}' already exists.")
        ws = sh.worksheet(SHEET_TAB_NAME)
    else:
        logger.info(f"Creating new worksheet tab '{SHEET_TAB_NAME}'...")
        ws = sh.add_worksheet(title=SHEET_TAB_NAME, rows=100, cols=26)
        logger.info(f"Worksheet tab '{SHEET_TAB_NAME}' created.")

    # Define headers
    headers = [
        "#", "Topic", "Level", "Status",
        "Word 1 (Hanzi)", "Word 1 Pinyin", "Word 1 Meaning",
        "Word 2 (Hanzi)", "Word 2 Pinyin", "Word 2 Meaning",
        "Word 3 (Hanzi)", "Word 3 Pinyin", "Word 3 Meaning",
        "Word 4 (Hanzi)", "Word 4 Pinyin", "Word 4 Meaning",
        "Word 5 (Hanzi)", "Word 5 Pinyin", "Word 5 Meaning",
        "Word 6 (Hanzi)", "Word 6 Pinyin", "Word 6 Meaning",
        "Video File", "GDrive Link", "Created At", "Notes"
    ]
    
    current_headers = ws.row_values(1)
    if not current_headers or current_headers != headers:
        logger.info("Setting headers in row 1...")
        ws.update("A1:Z1", [headers])
        # Format header row
        try:
            ws.format("A1:Z1", {
                "backgroundColor": {"red": 0.18, "green": 0.31, "blue": 0.31},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
                "horizontalAlignment": "CENTER"
            })
        except Exception as e:
            logger.warning(f"Could not format headers: {e}")

    # Check if we have sample data
    rows = ws.get_all_values()
    if len(rows) <= 1:
        logger.info("Adding initial sample row (HSK 1-2)...")
        sample_row = [
            "1",
            "HSK 1-2 Trái Cây & Trường Học",
            "HSK 1-2",
            "Pending",
            "苹果", "píng guǒ", "Quả táo",
            "老师", "lǎo shī", "Giáo viên",
            "学校", "xué xiào", "Trường học",
            "喜欢", "xǐ huan", "Thích",
            "中国", "zhōng guó", "Trung Quốc",
            "朋友", "péng you", "Bạn bè",
            "", "",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Batch 6 từ mẫu HSK 1-2"
        ]
        ws.append_row(sample_row)
        logger.info("Sample row added successfully.")

    logger.info(f"Tab '{SHEET_TAB_NAME}' is ready in spreadsheet {sh.title}!")

if __name__ == "__main__":
    init_pinyin_tab()
