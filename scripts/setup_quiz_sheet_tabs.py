import os
import sys
import time
import json
import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0"
CREDS_FILE = "/media/vpsg16gb/HaRiDisk/Telegram_Command_Center/service_account.json"

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
    "metadata",
    "Video",
    "Youtube",
    "Tiktok",
    "Facebook",
    "Created At",
    "Notes"
]

def main():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    print(f"Connecting to Google Sheets via {CREDS_FILE}...")
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=scopes)
    client = gspread.authorize(creds)
    
    ss = client.open_by_key(SPREADSHEET_ID)
    print(f"Opened Spreadsheet: '{ss.title}' (ID: {SPREADSHEET_ID})")
    
    existing_tabs = [ws.title for ws in ss.worksheets()]
    print(f"Existing tabs: {existing_tabs}")
    
    tabs_to_create = [
        ("vocabVN", "Tab Quiz Tiếng Việt ➔ Tiếng Trung (Amber Gold)"),
        ("vocabCN", "Tab Quiz Tiếng Trung ➔ Tiếng Việt (Emerald Green)")
    ]
    
    for tab_name, desc in tabs_to_create:
        if tab_name in existing_tabs:
            print(f"Tab '{tab_name}' already exists. Updating headers...")
            ws = ss.worksheet(tab_name)
        else:
            print(f"Creating tab '{tab_name}' ({desc})...")
            ws = ss.add_worksheet(title=tab_name, rows=200, cols=20)
            
        # Set Header row
        ws.update("A1:P1", [STANDARD_COLUMNS])
        
        # Format Header row: Freeze Row 1, Bold, Center Alignment
        try:
            # Freeze Row 1
            ws.freeze(rows=1)
            
            # Formatting header
            header_color = {"red": 0.96, "green": 0.62, "blue": 0.04} if tab_name == "vocabVN" else {"red": 0.06, "green": 0.72, "blue": 0.51}
            ws.format("A1:P1", {
                "backgroundColor": header_color,
                "textFormat": {"bold": True, "foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}},
                "horizontalAlignment": "CENTER"
            })
            print(f"Formatted header on tab '{tab_name}' successfully.")
        except Exception as fe:
            print(f"Note on header formatting: {fe}")
            
        print(f"✅ Tab '{tab_name}' is ready with standard 16 columns!")

if __name__ == "__main__":
    main()
