import os
import re
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.config import config

logger = logging.getLogger("MetadataGenerator")

def sanitize_filename(name: str) -> str:
    s = re.sub(r'[/\\:*?"<>|]', '_', name)
    return s.strip()

def clean_topic_display(topic: str) -> str:
    """Strip 'HSK 1 • ' prefix if needed for cleaner text."""
    parts = topic.split("•")
    if len(parts) > 1:
        return parts[1].strip()
    return topic.strip()

def generate_social_metadata(topic: str, level: str, words: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Generate viral, engaging metadata for YouTube Shorts, TikTok, and Facebook Reels.
    words: list of dicts with 'hanzi', 'pinyin', 'meaning'
    """
    clean_topic = clean_topic_display(topic)
    level_tag = level.replace(" ", "").upper()
    
    # Emoji mappings based on common topics
    emoji_map = {
        "Đồ Ăn": "🍎🍜",
        "Thức Uống": "🧋🥤",
        "Đời Sống": "🏠✨",
        "Gia Đình": "👨‍👩‍👧‍👦❤️",
        "Số Đếm": "🔢⏰",
        "Thời Gian": "⏳🕰️",
        "Địa Điểm": "🏫✈️",
        "Cảm Xúc": "😄🥰",
        "Mua Sắm": "🛍️🏷️",
        "Phương Tiện": "🚗🚌",
        "Thời Tiết": "☀️🌧️"
    }
    
    chosen_emoji = "🎯✨"
    for key, emo in emoji_map.items():
        if key.lower() in topic.lower():
            chosen_emoji = emo
            break

    # 1. YouTube Shorts Metadata
    yt_title = f"Thử Thách Đoán Pinyin {level}: {clean_topic} {chosen_emoji} | Lê Lê Học Tiếng Trung #Shorts"
    if len(yt_title) > 95:
        yt_title = f"Đoán Pinyin {level}: {clean_topic} {chosen_emoji} #Shorts"
        
    word_lines = []
    for idx, w in enumerate(words, start=1):
        hz = w.get("hanzi", "")
        py = w.get("pinyin", "")
        mean = w.get("meaning", "")
        word_lines.append(f"{idx}. {hz} ({py}): {mean}")
    words_formatted = "\n".join(word_lines)

    yt_description = f"""🎯 Thử thách đoán Pinyin tiếng Trung {level} chủ đề: {clean_topic.upper()}!
Bạn đoán đúng được bao nhiêu từ trên {len(words)} từ? Hãy comment số điểm của bạn bên dưới nhé! 👇

📚 DANH SÁCH TỪ VỰNG TRONG VIDEO:
{words_formatted}

🔔 Đừng quên bấm Like, Đăng ký kênh @lelehoctiengtrung và bật chuông thông báo để cùng luyện phản xạ tiếng Trung mỗi ngày cùng Lê Lê nhé!

#lelehoctiengtrung #hoctiengtrung #tiengtrunggiaotiep #pinyinquiz #{level_tag.lower()} #tiengtrungonline #Shorts #learnchinese #hsk
"""

    # 2. TikTok Metadata
    tiktok_caption = f"Đố bạn đoán đúng 5/5 Pinyin chủ đề {clean_topic} này? {chosen_emoji} Thử ngay xem bạn được mấy điểm nhé! 💬👇 #lelehoctiengtrung #hoctiengtrung #pinyin #tiengtrungmoibatdau #{level_tag.lower()} #pinyinquiz #xuhuong #learnchinese"

    # 3. Facebook Reels Metadata
    fb_caption = f"Thử tài phản xạ đoán Pinyin tiếng Trung {level} - Chủ đề {clean_topic}! {chosen_emoji}\nBạn tự tin đúng bao nhiêu câu? Comment kết quả bên dưới cùng Lê Lê nha! ✨\n\n#lelehoctiengtrung #tiengtrung #hoctiengtrung #pinyin #{level_tag.lower()} #reelsvn #hsk"

    # Combined Full Text for GDrive upload
    full_text = f"""===================================================================
METADATA CHO VIDEO: {topic} ({level})
Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
===================================================================

=== 1. YOUTUBE SHORTS ===
Tiêu đề (Title):
{yt_title}

Mô tả (Description):
{yt_description.strip()}

=== 2. TIKTOK ===
Caption & Hashtags:
{tiktok_caption}

=== 3. FACEBOOK REELS ===
Caption & Hashtags:
{fb_caption}
"""

    return {
        "youtube": {
            "title": yt_title,
            "description": yt_description.strip()
        },
        "tiktok": {
            "caption": tiktok_caption
        },
        "facebook": {
            "caption": fb_caption
        },
        "formatted_text": full_text
    }

def save_and_upload_metadata(
    batch_id: str,
    topic: str,
    level: str,
    words: List[Dict[str, str]],
    gdrive_uploader = None
) -> str:
    """
    Generate metadata, save local text file, and upload to Google Drive if uploader available.
    Returns Google Drive URL or local file path.
    """
    meta_dict = generate_social_metadata(topic, level, words)
    raw_text = meta_dict["formatted_text"]
    
    # Save local copy in output/metadata/
    meta_dir = os.path.join(config.base_dir, "output", "metadata")
    os.makedirs(meta_dir, exist_ok=True)
    
    clean_topic = sanitize_filename(topic)
    filename = f"#{batch_id}.{clean_topic}_metadata.txt"
    file_path = os.path.join(meta_dir, filename)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(raw_text)
    logger.info(f"Saved local metadata file: {file_path}")
    
    # Upload to Google Drive
    if gdrive_uploader:
        try:
            drive_url = gdrive_uploader.upload_file(file_path, filename)
            if drive_url:
                logger.info(f"Uploaded metadata to GDrive: {drive_url}")
                return drive_url
        except Exception as e:
            logger.error(f"Failed to upload metadata to GDrive: {e}")
            
    return file_path
