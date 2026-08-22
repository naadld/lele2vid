import os
import sys
import re
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("LLMClient")

DEFAULT_GEMINI_MODEL = "gemini-3.7-flash"

FALLBACK_VOCAB_BANK = [
    # HSK 1
    ("Gia Đình Thân Yêu", "HSK 1", [
        ("爸爸", "bà ba", "Bố / Ba"),
        ("妈妈", "mā ma", "Mẹ"),
        ("儿子", "ér zi", "Con trai"),
        ("女儿", "nǚ ér", "Con gái"),
        ("朋友", "péng you", "Bạn bè")
    ]),
    ("Thời Gian Hàng Ngày", "HSK 1", [
        ("今天", "jīn tiān", "Hôm nay"),
        ("明天", "míng tiān", "Ngày mai"),
        ("昨天", "zuó tiān", "Hôm qua"),
        ("现在", "xiàn zài", "Bây giờ"),
        ("点钟", "diǎn zhōng", "Giờ giấc")
    ]),
    ("Đồ Ăn & Thức Uống", "HSK 1", [
        ("米饭", "mǐ fàn", "Cơm"),
        ("面条", "miàn tiáo", "Mì sợi"),
        ("苹果", "píng guǒ", "Quả táo"),
        ("茶水", "chá shuǐ", "Nước trà"),
        ("牛奶", "niú nǎi", "Sữa tươi")
    ]),
    # HSK 2
    ("Giao Tiếp Xã Hội", "HSK 2", [
        ("帮助", "bāng zhù", "Giúp đỡ"),
        ("介绍", "jiè shào", "Giới thiệu"),
        ("欢迎", "huān yíng", "Chào đón"),
        ("希望", "xī wàng", "Hy vọng"),
        ("准备", "zhǔn bèi", "Chuẩn bị")
    ]),
    ("Phương Tiện Giao Thông", "HSK 2", [
        ("公共汽车", "gōng gòng qì chē", "Xe buýt"),
        ("出租车", "chū zū chē", "Xe taxi"),
        ("自行车", "zì xíng chē", "Xe đạp"),
        ("火车站", "huǒ chē zhàn", "Ga tàu hỏa"),
        ("飞机场", "fēi jī chǎng", "Sân bay")
    ]),
    # HSK 3
    ("Môi Trường Làm Việc", "HSK 3", [
        ("同事", "tóng shì", "Đồng nghiệp"),
        ("会议", "huì yì", "Cuộc họp"),
        ("经理", "jīng lǐ", "Giám đốc / Quản lý"),
        ("薪水", "xīn shui", "Tiền lương"),
        ("加班", "jiā bān", "Tăng ca")
    ])
]

def parse_gemini_keys() -> List[str]:
    raw = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or ""
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    return keys

def mask_key(k: str) -> str:
    if len(k) <= 8:
        return "***"
    return f"{k[:4]}...{k[-4:]}"
