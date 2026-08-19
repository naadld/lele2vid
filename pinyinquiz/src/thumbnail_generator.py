import os
import sys
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
    shadow_offset: tuple = (5, 5),
    anchor: str = "mm"
):
    """Draw text with high-contrast drop shadow for maximum readability."""
    x, y = xy
    sx, sy = shadow_offset
    # Draw shadow
    draw.text((x + sx, y + sy), text, font=font, fill=shadow_color, anchor=anchor)
    # Draw text
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)

def clean_topic_title(raw_topic: str) -> str:
    """Clean topic title by removing redundant 'HSK X • ' prefixes."""
    t = raw_topic.strip()
    if "•" in t:
        parts = t.split("•", 1)
        t = parts[1].strip()
    elif "-" in t:
        parts = t.split("-", 1)
        t = parts[1].strip()
    return t.upper()

def wrap_text(text: str, max_chars_per_line: int = 14) -> list:
    """Wrap long topic title into clean balanced lines."""
    words = text.split()
    lines = []
    curr = []
    curr_len = 0
    for w in words:
        if curr_len + len(w) + (1 if curr else 0) <= max_chars_per_line:
            curr.append(w)
            curr_len += len(w) + (1 if len(curr) > 1 else 0)
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
            curr_len = len(w)
    if curr:
        lines.append(" ".join(curr))
    return lines if lines else [text]

def create_high_ctr_thumbnail(batch_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generate a clean, high-impact 1080x1920 9:16 vertical thumbnail:
    - Top: HSK Level Badge
    - Middle: Huge Topic Title (Chủ đề ở giữa, chữ cực to)
    - Bottom: Pinyin trong 5 giây (Pinyin in 5 seconds Badge)
    """
    width = 1080
    height = 1920
    
    raw_topic = batch_data.get("topic", "ĐỒ ĂN & THỨC UỐNG")
    level = batch_data.get("level", "HSK 1").upper()
    batch_id = batch_data.get("id", "0")
    topic_clean = clean_topic_title(raw_topic)

    # 1. Base Canvas & Cinematic Background
    bg_img_path = os.path.join(config.base_dir, "assets", "images", "background.jpg")
    if os.path.exists(bg_img_path):
        base_bg = Image.open(bg_img_path).convert("RGBA")
        base_bg = base_bg.resize((width, height), Image.Resampling.LANCZOS)
        # Apply smooth blur to background
        base_bg = base_bg.filter(ImageFilter.GaussianBlur(radius=10))
    else:
        base_bg = Image.new("RGBA", (width, height), "#090d16")

    # Dark gradient vignette overlay
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    for y in range(height):
        # Darkness from 0.50 in center to 0.88 at edges
        dist = abs(y - height / 2) / (height / 2)
        alpha = int(140 + 85 * (dist ** 1.3))
        overlay_draw.line([(0, y), (width, y)], fill=(4, 7, 20, min(alpha, 245)))

    combined = Image.alpha_composite(base_bg, overlay)
    draw = ImageDraw.Draw(combined)

    # =========================================================================
    # 1. PHẦN TRÊN CÙNG: LEVEL HSK (Gọn gàng, nổi bật, sang trọng)
    # =========================================================================
    top_badge_y = 380
    badge_w = 420
    badge_h = 100
    bx1 = int((width - badge_w) / 2)
    by1 = int(top_badge_y - badge_h / 2)
    bx2 = bx1 + badge_w
    by2 = by1 + badge_h

    # Glowing border
    draw_rounded_rect(
        draw,
        (bx1 - 4, by1 - 4, bx2 + 4, by2 + 4),
        radius=52,
        fill=None,
        outline="#38bdf8",
        width=3
    )
    # Badge background (Cyan gradient look)
    draw_rounded_rect(
        draw,
        (bx1, by1, bx2, by2),
        radius=50,
        fill="#0284c7",
        outline="#7dd3fc",
        width=3
    )

    font_level = get_font(52, bold=True)
    level_label = level if "HSK" in level else f"HSK {level}"
    draw_text_with_shadow(
        draw,
        (width / 2, top_badge_y),
        level_label,
        font_level,
        fill="#ffffff",
        shadow_color="#082f49",
        shadow_offset=(3, 3),
        anchor="mm"
    )

    # =========================================================================
    # 2. PHẦN Ở GIỮA: CHỦ ĐỀ CHỮ CỰC TO & NỔI BẬT (TÂM ĐIỂM CHÍNH)
    # =========================================================================
    topic_lines = wrap_text(topic_clean, max_chars_per_line=13)
    
    # Calculate card height based on lines
    num_lines = len(topic_lines)
    line_spacing = 130 if num_lines <= 2 else 115
    font_size = 96 if num_lines <= 2 else 82
    font_topic = get_font(font_size, bold=True)

    card_padding_v = 110
    card_h = (num_lines * line_spacing) + card_padding_v * 2
    card_y_center = 960
    card_y1 = int(card_y_center - card_h / 2)
    card_y2 = card_y1 + card_h
    card_x1 = 70
    card_x2 = width - 70

    # Outer Neon Glow Frame
    draw_rounded_rect(
        draw,
        (card_x1 - 6, card_y1 - 6, card_x2 + 6, card_y2 + 6),
        radius=46,
        fill=None,
        outline="#f59e0b",
        width=4
    )
    # Central Glass Card
    draw_rounded_rect(
        draw,
        (card_x1, card_y1, card_x2, card_y2),
        radius=40,
        fill=(15, 23, 42, 240),
        outline="#fbbf24",
        width=4
    )

    # Draw each line of Topic with Gold color & 3D shadow
    first_line_y = card_y_center - ((num_lines - 1) * line_spacing) / 2
    for i, line_text in enumerate(topic_lines):
        ly = int(first_line_y + i * line_spacing)
        draw_text_with_shadow(
            draw,
            (width / 2, ly),
            line_text,
            font_topic,
            fill="#fde047",
            shadow_color="#78350f",
            shadow_offset=(6, 6),
            anchor="mm"
        )

    # =========================================================================
    # 3. PHẦN BÊN DƯỚI: PINYIN TRONG 5 GIÂY
    # =========================================================================
    bottom_badge_y = 1520
    b_badge_w = 760
    b_badge_h = 120
    bbx1 = int((width - b_badge_w) / 2)
    bby1 = int(bottom_badge_y - b_badge_h / 2)
    bbx2 = bbx1 + b_badge_w
    bby2 = bby1 + b_badge_h

    # Outer Neon Glow
    draw_rounded_rect(
        draw,
        (bbx1 - 5, bby1 - 5, bbx2 + 5, bby2 + 5),
        radius=65,
        fill=None,
        outline="#ff0055",
        width=4
    )
    # Bottom Red-Pink Vibrant Badge
    draw_rounded_rect(
        draw,
        (bbx1, bby1, bbx2, bby2),
        radius=60,
        fill="#e11d48",
        outline="#fda4af",
        width=3
    )

    font_bottom = get_font(52, bold=True)
    draw_text_with_shadow(
        draw,
        (width / 2, bottom_badge_y),
        "PINYIN TRONG 5 GIÂY",
        font_bottom,
        fill="#ffffff",
        shadow_color="#4c0519",
        shadow_offset=(4, 4),
        anchor="mm"
    )

    # Save Output File
    if not output_path:
        clean_topic_name = "".join([c if c.isalnum() else "_" for c in raw_topic]).strip("_")
        output_filename = f"#{batch_id}.{clean_topic_name}_thumbnail.jpg"
        output_path = os.path.join(config.output_videos_dir, output_filename)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save as high-quality progressive JPEG
    rgb_img = combined.convert("RGB")
    rgb_img.save(output_path, "JPEG", quality=95, optimize=True)
    logger.info(f"✨ Minimal High-Impact Thumbnail generated successfully: {output_path}")
    return output_path

if __name__ == "__main__":
    test_batch = {
        "id": "2",
        "topic": "HSK 1 • Đồ Ăn & Thức Uống",
        "level": "HSK 1",
        "words": []
    }
    path = create_high_ctr_thumbnail(test_batch, "/media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz/output/#2.HSK_1_Do_An_Thuc_Uong_thumbnail.jpg")
    print("Generated Minimal Thumbnail for Row 2:", path)
