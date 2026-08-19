import os
import sys
import math
import logging
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import config

logger = logging.getLogger("ThumbnailGenerator")

# Standard CJK and Latin Font Paths
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/litefonts/ARIALUNI.TTF",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Find and load available TrueType font."""
    for font_path in FONT_CANDIDATES:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()

def draw_rounded_rect(draw: ImageDraw.ImageDraw, xy, radius: int, fill=None, outline=None, width=1):
    """Draw a smooth rounded rectangle."""
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def draw_text_with_shadow(
    draw: ImageDraw.ImageDraw,
    xy,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str = "#ffffff",
    shadow_color: str = "#000000",
    shadow_offset: tuple = (3, 3),
    anchor: str = "mm"
):
    """Draw text with high-contrast drop shadow for maximum readability."""
    x, y = xy
    sx, sy = shadow_offset
    # Draw shadow
    draw.text((x + sx, y + sy), text, font=font, fill=shadow_color, anchor=anchor)
    # Draw text
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)

def create_high_ctr_thumbnail(batch_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generate an eye-catching, high-CTR 1080x1920 9:16 vertical thumbnail for TikTok/Shorts/Reels.
    """
    width = 1080
    height = 1920
    
    topic = batch_data.get("topic", "HSK 1-2 • ĐOÁN TỪ VỰNG")
    level = batch_data.get("level", "HSK 1-2")
    words = batch_data.get("words", [])
    batch_id = batch_data.get("id", "0")

    # Pick the most interesting word for the hero teaser
    hero_word = words[0] if words else {"hanzi": "汉语", "pinyin": "hàn yǔ", "hidden_pinyin": "h _ _   y _", "meaning": "Tiếng Trung"}
    if len(words) >= 3:
        hero_word = words[1]

    hz = hero_word.get("hanzi", "中文")
    py = hero_word.get("pinyin", "")
    hidden_py = hero_word.get("hidden_pinyin", "")
    meaning = hero_word.get("meaning", "")

    # 1. Base Canvas & Background
    bg_img_path = os.path.join(config.base_dir, "assets", "images", "background.jpg")
    if os.path.exists(bg_img_path):
        base_bg = Image.open(bg_img_path).convert("RGBA")
        base_bg = base_bg.resize((width, height), Image.Resampling.LANCZOS)
        # Apply slight blur to background to make foreground pop
        base_bg = base_bg.filter(ImageFilter.GaussianBlur(radius=8))
    else:
        base_bg = Image.new("RGBA", (width, height), "#0f172a")

    # Overlay dark gradient for high contrast
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # Top & bottom vignette
    for y in range(height):
        alpha = int(120 + 90 * (abs(y - height / 2) / (height / 2)) ** 1.5)
        overlay_draw.line([(0, y), (width, y)], fill=(3, 7, 18, min(alpha, 240)))

    combined = Image.alpha_composite(base_bg, overlay)
    draw = ImageDraw.Draw(combined)

    # 2. Top Super Badge: "🔥 THỬ THÁCH TIẾNG TRUNG • 99% ĐOÁN SAI!"
    top_badge_y = 260
    draw_rounded_rect(
        draw,
        (100, top_badge_y - 45, width - 100, top_badge_y + 45),
        radius=45,
        fill="#ff0055",
        outline="#ff77aa",
        width=3
    )
    font_badge = get_font(36, bold=True)
    draw.text((width / 2, top_badge_y), "🔥 THỬ THÁCH HSK • BẠN ĐOÁN ĐƯỢC 5/5?", font=font_badge, fill="#ffffff", anchor="mm")

    # 3. Main Hook Header (Huge & Bold): "ĐỐ BẠN BIẾT TỪ NÀY?"
    header_y = 420
    font_hook = get_font(68, bold=True)
    draw_text_with_shadow(
        draw,
        (width / 2, header_y),
        "ĐỐ BẠN BIẾT TỪ NÀY?",
        font_hook,
        fill="#facc15",
        shadow_color="#000000",
        shadow_offset=(4, 4),
        anchor="mm"
    )

    # Topic Sub-Pill
    topic_pill_y = 530
    draw_rounded_rect(
        draw,
        (140, topic_pill_y - 35, width - 140, topic_pill_y + 35),
        radius=35,
        fill="#0284c7",
        outline="#38bdf8",
        width=2
    )
    font_topic = get_font(34, bold=True)
    draw.text((width / 2, topic_pill_y), f"📚 {topic.upper()}", font=font_topic, fill="#ffffff", anchor="mm")

    # 4. Central Hero Card (Glassmorphism & Neon Glow)
    card_x1, card_y1 = 80, 640
    card_x2, card_y2 = width - 80, 1380
    
    # Outer Glow Border
    draw_rounded_rect(
        draw,
        (card_x1 - 6, card_y1 - 6, card_x2 + 6, card_y2 + 6),
        radius=46,
        fill=None,
        outline="#00f0ff",
        width=4
    )
    # Card Background
    draw_rounded_rect(
        draw,
        (card_x1, card_y1, card_x2, card_y2),
        radius=40,
        fill=(15, 23, 42, 235),
        outline="#38bdf8",
        width=3
    )

    # Question Header in Card
    card_header_y = card_y1 + 80
    font_card_head = get_font(38, bold=True)
    draw.text((width / 2, card_header_y), "🇨🇳 PHIÊN ÂM CHUẨN LÀ GÌ? 🇨🇳", font=font_card_head, fill="#38bdf8", anchor="mm")

    # Giant Chinese Character (Hanzi)
    hanzi_y = card_y1 + 270
    font_hanzi = get_font(180, bold=True)
    draw_text_with_shadow(
        draw,
        (width / 2, hanzi_y),
        hz,
        font_hanzi,
        fill="#ffffff",
        shadow_color="#0284c7",
        shadow_offset=(6, 6),
        anchor="mm"
    )

    # Mystery Pinyin Box with blanks and question marks
    pinyin_box_y = card_y1 + 470
    draw_rounded_rect(
        draw,
        (140, pinyin_box_y - 55, width - 140, pinyin_box_y + 55),
        radius=30,
        fill="#1e293b",
        outline="#f59e0b",
        width=3
    )
    
    display_pinyin_teaser = hidden_py if hidden_py else f"{py[:2]} _ _ _ ?"
    font_pinyin = get_font(60, bold=True)
    draw.text((width / 2, pinyin_box_y), f"❓  {display_pinyin_teaser}  ❓", font=font_pinyin, fill="#fbbf24", anchor="mm")

    # Vietnamese Meaning Teaser
    meaning_y = card_y1 + 610
    font_meaning = get_font(46, bold=True)
    draw.text((width / 2, meaning_y), f"Nghĩa: \"{meaning}\"", font=font_meaning, fill="#a7f3d0", anchor="mm")

    # 5. Timer & Score Badge Teaser
    badge_info_y = 1460
    draw_rounded_rect(
        draw,
        (180, badge_info_y - 40, width - 180, badge_info_y + 40),
        radius=40,
        fill="#dc2626",
        outline="#f87171",
        width=2
    )
    font_info = get_font(34, bold=True)
    draw.text((width / 2, badge_info_y), f"⏱️ 5 GIÂY / CÂU • CẤP ĐỘ {level.upper()}", font=font_info, fill="#ffffff", anchor="mm")

    # 6. Bottom Big CTA Button (Click-Through Magnet)
    cta_y = 1620
    draw_rounded_rect(
        draw,
        (100, cta_y - 65, width - 100, cta_y + 65),
        radius=50,
        fill="#10b981",
        outline="#34d399",
        width=4
    )
    font_cta = get_font(48, bold=True)
    draw_text_with_shadow(
        draw,
        (width / 2, cta_y),
        "👉 XEM VIDEO ĐỂ TRẢ LỜI 👈",
        font_cta,
        fill="#ffffff",
        shadow_color="#064e3b",
        shadow_offset=(3, 3),
        anchor="mm"
    )

    # 7. Channel Signature Watermark & Avatar
    footer_y = 1790
    font_footer = get_font(32, bold=True)
    draw.text((width / 2, footer_y), "✨ Kênh: Lê Lê Học Tiếng Trung (HSK Quiz 24/7) ✨", font=font_footer, fill="#94a3b8", anchor="mm")

    # Save Output File
    if not output_path:
        clean_topic = "".join([c if c.isalnum() else "_" for c in topic]).strip("_")
        output_filename = f"#{batch_id}.{clean_topic}_thumbnail.jpg"
        output_path = os.path.join(config.output_videos_dir, output_filename)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save as high-quality progressive JPEG
    rgb_img = combined.convert("RGB")
    rgb_img.save(output_path, "JPEG", quality=95, optimize=True)
    logger.info(f"✨ High-CTR Thumbnail generated successfully: {output_path}")
    return output_path

if __name__ == "__main__":
    test_batch = {
        "id": "1",
        "topic": "HSK 1 • Đồ Ăn & Thức Uống",
        "level": "HSK 1",
        "words": [
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "hidden_pinyin": "m _   f _ _", "meaning": "Cơm trắng"},
            {"hanzi": "苹果", "pinyin": "píng guǒ", "hidden_pinyin": "p _ _ _   g _ _", "meaning": "Quả táo"}
        ]
    }
    path = create_high_ctr_thumbnail(test_batch, "/media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz/output/test_thumbnail.jpg")
    print("Generated Test Thumbnail:", path)
