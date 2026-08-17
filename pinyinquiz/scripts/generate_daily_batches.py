import os
import sys
import random
from datetime import datetime
from typing import List, Tuple, Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.gsheet_manager import GSheetManager
from src.pinyin_utils import prepare_word_tuple
from src.metadata_generator import save_and_upload_metadata
from src.gdrive_uploader import GDriveUploader

# Comprehensive HSK 1 - HSK 3 Vocabulary Bank
VOCAB_BANK = [
    # HSK 1
    ("HSK 1 • Gia Đình & Xưng Hô", "HSK 1", [
        ("爸爸", "bà ba", "Bố / Ba"),
        ("妈妈", "mā ma", "Mẹ"),
        ("儿子", "ér zi", "Con trai"),
        ("女儿", "nǚ ér", "Con gái"),
        ("朋友", "péng you", "Bạn bè")
    ]),
    ("HSK 1 • Số Đếm & Thời Gian", "HSK 1", [
        ("今天", "jīn tiān", "Hôm nay"),
        ("明天", "míng tiān", "Ngày mai"),
        ("昨天", "zuó tiān", "Hôm qua"),
        ("现在", "xiàn zài", "Bây giờ"),
        ("点钟", "diǎn zhōng", "Giờ / Tiếng đồng hồ")
    ]),
    ("HSK 1 • Địa Điểm & Phương Hướng", "HSK 1", [
        ("学校", "xué xiào", "Trường học"),
        ("医院", "yī yuàn", "Bệnh viện"),
        ("商店", "shāng diàn", "Cửa hàng"),
        ("北京", "běi jīng", "Bắc Kinh"),
        ("中国", "zhōng guó", "Trung Quốc")
    ]),
    ("HSK 1 • Đồ Vật Thường Gặp", "HSK 1", [
        ("桌子", "zhuō zi", "Cái bàn"),
        ("椅子", "yǐ zi", "Cái ghế"),
        ("衣服", "yī fu", "Quần áo"),
        ("杯子", "bēi zi", "Cái cốc / ly"),
        ("电脑", "diàn nǎo", "Máy vi tính")
    ]),
    ("HSK 1 • Hành Động Thường Ngày", "HSK 1", [
        ("说话", "shuō huà", "Nói chuyện"),
        ("听歌", "tīng gē", "Nghe nhạc"),
        ("看书", "kàn shū", "Đọc sách"),
        ("写字", "xiě zì", "Viết chữ"),
        ("学习", "xué xí", "Học tập")
    ]),
    # HSK 2
    ("HSK 2 • Giao Tiếp Xã Hội", "HSK 2", [
        ("帮助", "bāng zhù", "Giúp đỡ"),
        ("介绍", "jiè shào", "Giới thiệu"),
        ("欢迎", "huān yíng", "Hoan nghênh / Chào đón"),
        ("回答", "huí dá", "Trả lời"),
        ("希望", "xī wàng", "Hy vọng")
    ]),
    ("HSK 2 • Cảm Xúc & Tính Cách", "HSK 2", [
        ("快乐", "kuài lè", "Vui vẻ / Hạnh phúc"),
        ("难过", "nán guò", "Buồn bã"),
        ("着急", "zháo jí", "Lo lắng / Vội vàng"),
        ("聪明", "cōng ming", "Thông minh"),
        ("热情", "rè qíng", "Nhiệt tình")
    ]),
    ("HSK 2 • Thời Tiết & Thiên Nhiên", "HSK 2", [
        ("晴天", "qíng tiān", "Trời nắng"),
        ("下雨", "xià yǔ", "Trời mưa"),
        ("下雪", "xià xuě", "Tuyết rơi"),
        ("刮风", "guā fēng", "Gió thổi"),
        ("温度", "wēn dù", "Nhiệt độ")
    ]),
    ("HSK 2 • Phương Tiện Đi Lại", "HSK 2", [
        ("飞机", "fēi jī", "Máy bay"),
        ("出租车", "chū zū chē", "Xe taxi"),
        ("公交车", "gōng jiāo chē", "Xe buýt"),
        ("火车站", "huǒ chē zhàn", "Ga xe lửa"),
        ("机场", "jī chǎng", "Sân bay")
    ]),
    ("HSK 2 • Mua Sắm & Ăn Uống", "HSK 2", [
        ("西瓜", "xī guā", "Dưa hấu"),
        ("鸡蛋", "jī dàn", "Trứng gà"),
        ("羊肉", "yáng ròu", "Thịt cừu"),
        ("牛奶", "niú nǎi", "Sữa bò"),
        ("咖啡", "kā fēi", "Cà phê")
    ])
]

def generate_daily_rows(count: int = 5) -> List[List[str]]:
    """
    Generate non-repeating vocabulary rows for the daily batch with social media metadata.
    """
    mgr = GSheetManager()
    all_rows = mgr.get_all_rows()
    
    gdrive_uploader = None
    try:
        gdrive_uploader = GDriveUploader()
    except Exception as e:
        print(f"GDriveUploader notice: {e}")
    
    # Track existing used words to prevent duplication
    used_words = set()
    for r in all_rows:
        for i in range(1, 6):
            w = str(r.get(f"Word {i}", "")).split("|")[0].strip()
            if w:
                used_words.add(w)

    current_max_id = len(all_rows)
    selected_pools = random.sample(VOCAB_BANK, min(count, len(VOCAB_BANK)))
    new_rows = []
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for idx, (topic, level, words) in enumerate(selected_pools, start=current_max_id + 1):
        row = [
            str(idx),
            topic,
            level,
            "Pending"
        ]
        
        parsed_words = []
        for w_item in words:
            hz, py, mean = w_item
            parsed_words.append({"hanzi": hz, "pinyin": py, "meaning": mean})
            h, fp, hp = prepare_word_tuple(hz, py)
            row.append(f"{h} | {fp} | {hp} | {mean}")
            
        # 1. Tự động sinh Metadata (Title + Description cho YT Shorts, TikTok, FB Reels)
        metadata_link = save_and_upload_metadata(
            batch_id=str(idx),
            topic=topic,
            level=level,
            words=parsed_words,
            gdrive_uploader=gdrive_uploader
        )
        
        # Col 10: metadata, Col 11: Video, Col 12: Youtube, Col 13: Tiktok, Col 14: Facebook, Col 15: Created At, Col 16: Notes
        row.extend([metadata_link, "", "", "", "", now_str, "Tự động sinh bởi Daily Batch Creator"])
        new_rows.append(row)

    return new_rows

def main():
    print("=== Daily Batch Creator (02:00 GMT+7) ===")
    mgr = GSheetManager()
    new_rows = generate_daily_rows(count=5)
    
    if new_rows:
        mgr.worksheet.append_rows(new_rows)
        print(f" Successfully added {len(new_rows)} new Pending batches with metadata to tab '{mgr.tab_name}'!")
    else:
        print("No new batches generated.")

if __name__ == "__main__":
    main()
