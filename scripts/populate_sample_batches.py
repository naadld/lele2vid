import os
import sys
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.gsheet_manager import GSheetManager, STANDARD_COLUMNS
from src.pinyin_utils import prepare_word_tuple

SAMPLE_BATCHES = [
    {
        "id": "1",
        "topic": "HSK 1 • Đồ Ăn & Thức Uống",
        "level": "HSK 1",
        "words": [
            ("苹果", "píng guǒ", "Quả táo"),
            ("米饭", "mǐ fàn", "Cơm"),
            ("面包", "miàn bāo", "Bánh mì"),
            ("喝水", "hē shuǐ", "Uống nước"),
            ("吃饭", "chī fàn", "Ăn cơm")
        ]
    },
    {
        "id": "2",
        "topic": "HSK 1 • Đời Sống Hằng Ngày",
        "level": "HSK 1",
        "words": [
            ("看书", "kàn shū", "Đọc sách"),
            ("睡觉", "shuì jiào", "Đi ngủ"),
            ("买菜", "mǎi cài", "Đi chợ mua đồ"),
            ("回家", "huí jiā", "Về nhà"),
            ("打电话", "dǎ diàn huà", "Gọi điện thoại")
        ]
    },
    {
        "id": "3",
        "topic": "HSK 2 • Cảm Xúc & Hành Động",
        "level": "HSK 2",
        "words": [
            ("高兴", "gāo xìng", "Vui vẻ"),
            ("生病", "shēng bìng", "Bị ốm"),
            ("跑步", "pǎo bù", "Chạy bộ"),
            ("唱歌", "chàng gē", "Ca hát"),
            ("旅游", "lǚ yóu", "Du lịch")
        ]
    },
    {
        "id": "4",
        "topic": "HSK 2 • Mua Sắm & Giao Tiếp",
        "level": "HSK 2",
        "words": [
            ("便宜", "pián yi", "Rẻ tiền"),
            ("贵", "guì", "Đắt tiền"),
            ("帮助", "bāng zhù", "Giúp đỡ"),
            ("准备", "zhǔn bèi", "Chuẩn bị"),
            ("介绍", "jiè shào", "Giới thiệu")
        ]
    }
]

def main():
    print("Connecting to Google Sheets...")
    mgr = GSheetManager()
    
    # Re-initialize Header with 5-words standard
    mgr.worksheet.clear()
    mgr.worksheet.update("A1:M1", [STANDARD_COLUMNS])
    print("Updated Header schema for 5 words.")
    
    rows_to_insert = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for b in SAMPLE_BATCHES:
        row = [
            b["id"],
            b["topic"],
            b["level"],
            "Pending",
        ]
        # Word 1..5
        for item in b["words"]:
            hz, py, mean = item
            h, fp, hp = prepare_word_tuple(hz, py)
            row.append(f"{h} | {fp} | {hp} | {mean}")
            
        # Video File, GDrive Link, Created At, Notes
        row.extend(["", "", now_str, "Tự động tạo bởi lelehoctiengtrung_pinyin"])
        rows_to_insert.append(row)
        
    mgr.worksheet.append_rows(rows_to_insert)
    print(f"Successfully populated {len(rows_to_insert)} batches (5 words/video) into sheet tab '{mgr.tab_name}'!")

if __name__ == "__main__":
    main()
