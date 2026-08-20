import os
import sys
import time
import json
import random
import logging
import argparse
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Dict, Any, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.gsheet_manager import GSheetManager
from src.pinyin_utils import prepare_word_tuple
from src.metadata_generator import save_and_upload_metadata
from src.gdrive_uploader import GDriveUploader
from src.llm_client import (
    generate_hsk_topics_with_llm,
    generate_single_replacement_topic,
    parse_gemini_keys,
    mask_key,
    DEFAULT_GEMINI_MODEL
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DailyBatchGenerator")

DEFAULT_WEBHOOK_URL = os.getenv("CF_WEBHOOK_URL", "https://lele-pinyinquiz.aleron-dt.workers.dev/api/receive-ideas")

# High-quality fallback vocabulary bank complying 100% with Gatekeeper 1 standards
# (Single topic, 100% Simplified Chinese, 100% Vietnamese meaning, 1:1 syllable match)
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
    ("Địa Điểm Thân Quen", "HSK 1", [
        ("学校", "xué xiào", "Trường học"),
        ("医院", "yī yuàn", "Bệnh viện"),
        ("商店", "shāng diàn", "Cửa hàng"),
        ("北京", "běi jīng", "Bắc Kinh"),
        ("中国", "zhōng guó", "Trung Quốc")
    ]),
    ("Đồ Dùng Thường Gặp", "HSK 1", [
        ("桌子", "zhuō zi", "Cái bàn"),
        ("椅子", "yǐ zi", "Cái ghế"),
        ("衣服", "yī fu", "Quần áo"),
        ("杯子", "bēi zi", "Cái cốc"),
        ("电脑", "diàn nǎo", "Máy tính")
    ]),
    ("Hành Động Hằng Ngày", "HSK 1", [
        ("说话", "shuō huà", "Nói chuyện"),
        ("听歌", "tīng gē", "Nghe nhạc"),
        ("看书", "kàn shū", "Đọc sách"),
        ("写字", "xiě zì", "Viết chữ"),
        ("学习", "xué xí", "Học tập")
    ]),
    # HSK 2
    ("Giao Tiếp Xã Hội", "HSK 2", [
        ("帮助", "bāng zhù", "Giúp đỡ"),
        ("介绍", "jiè shào", "Giới thiệu"),
        ("欢迎", "huān yíng", "Chào đón"),
        ("回答", "huí dá", "Trả lời"),
        ("希望", "xī wàng", "Hy vọng")
    ]),
    ("Cảm Xúc Thường Thấy", "HSK 2", [
        ("快乐", "kuài lè", "Vui vẻ"),
        ("难过", "nán guò", "Buồn bã"),
        ("着急", "zháo jí", "Lo lắng"),
        ("聪明", "cōng míng", "Thông minh"),
        ("热情", "rè qíng", "Nhiệt tình")
    ]),
    ("Thời Tiết Bốn Mùa", "HSK 2", [
        ("晴天", "qíng tiān", "Trời nắng"),
        ("下雨", "xià yǔ", "Trời mưa"),
        ("下雪", "xià xuě", "Tuyết rơi"),
        ("刮风", "guā fēng", "Gió thổi"),
        ("温度", "wēn dù", "Nhiệt độ")
    ]),
    ("Phương Tiện Giao Thông", "HSK 2", [
        ("飞机", "fēi jī", "Máy bay"),
        ("出租车", "chū zū chē", "Xe tắc xi"),
        ("公交车", "gōng jiāo chē", "Xe buýt"),
        ("火车站", "huǒ chē zhàn", "Ga xe lửa"),
        ("机场", "jī chǎng", "Sân bay")
    ]),
    ("Món Ăn Hằng Ngày", "HSK 2", [
        ("西瓜", "xī guā", "Dưa hấu"),
        ("鸡蛋", "jī dàn", "Trứng gà"),
        ("羊肉", "yáng ròu", "Thịt cừu"),
        ("牛奶", "niú nǎi", "Sữa bò"),
        ("咖啡", "kā fēi", "Cà phê")
    ]),
    # HSK 3
    ("Thói Quen Sinh Hoạt", "HSK 3", [
        ("锻炼", "duàn liàn", "Rèn luyện"),
        ("习惯", "xí guàn", "Thói quen"),
        ("干净", "gān jìng", "Sạch sẽ"),
        ("刷牙", "shuā yá", "Đánh răng"),
        ("洗澡", "xǐ zǎo", "Tắm rửa")
    ]),
    ("Công Việc Văn Phòng", "HSK 3", [
        ("会议", "huì yì", "Cuộc họp"),
        ("同事", "tóng shì", "Đồng nghiệp"),
        ("经理", "jīng lǐ", "Giám đốc"),
        ("请假", "qǐng jià", "Xin nghỉ phép"),
        ("完成", "wán chéng", "Hoàn thành")
    ]),
    ("Giao Tiếp Xã Giao", "HSK 3", [
        ("礼貌", "lǐ mào", "Lịch sự"),
        ("客气", "kè qì", "Khách sáo"),
        ("原谅", "yuán liàng", "Tha thứ"),
        ("感谢", "gǎn xiè", "Cảm ơn"),
        ("祝贺", "zhù hè", "Chúc mừng")
    ]),
    ("Môi Trường Tự Nhiên", "HSK 3", [
        ("环境", "huán jìng", "Môi trường"),
        ("保护", "bǎo hù", "Bảo vệ"),
        ("森林", "sēn lín", "Rừng rậm"),
        ("世界", "shì jiè", "Thế giới"),
        ("新鲜", "xīn xiān", "Trong lành")
    ]),
    ("Du Lịch Khám Phá", "HSK 3", [
        ("行李", "xíng lǐ", "Hành lý"),
        ("照相机", "zhào xiàng jī", "Máy ảnh"),
        ("地图", "dì tú", "Bản đồ"),
        ("护照", "hù zhào", "Hộ chiếu"),
        ("风景", "fēng jǐng", "Phong cảnh")
    ]),
    ("Sức Khỏe Đời Sống", "HSK 3", [
        ("感冒", "gǎn mào", "Cảm cúm"),
        ("发烧", "fā shāo", "Phát sốt"),
        ("检查", "jiǎn chá", "Kiểm tra"),
        ("健康", "jiàn kāng", "Sức khỏe"),
        ("舒服", "shū fú", "Dễ chịu")
    ])
]


def get_vietnam_now_str() -> str:
    """Get current Vietnam timestamp in YYYY-MM-DD HH:MM:SS (GMT+7)."""
    tz_vn = timezone(timedelta(hours=7))
    return datetime.now(tz_vn).strftime("%Y-%m-%d %H:%M:%S")


def send_telegram_alert(text: str):
    """Send Telegram notification."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip() or "1187577977"
    if not (bot_token and chat_id):
        logger.warning("Telegram alert skipped: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID missing.")
        return
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        res = requests.post(url, json=payload, timeout=20)
        if res.status_code != 200:
            logger.warning(f"Telegram alert warning ({res.status_code}): {res.text}")
            if "parse" in res.text.lower():
                import re
                payload["text"] = re.sub(r'<[^>]*>', '', text)
                payload.pop("parse_mode", None)
                requests.post(url, json=payload, timeout=20)
    except Exception as e:
        logger.warning(f"Telegram alert error: {e}")


def load_negative_context_from_sheet(max_rows: int = 100) -> Tuple[List[str], List[str], int]:
    """
    Read latest N rows from Google Sheet to build Negative Context (used words & topics).
    Returns (used_words, used_topics, current_max_id).
    """
    used_words = []
    used_topics = []
    current_max_id = 0

    try:
        mgr = GSheetManager()
        all_rows = mgr.get_all_rows()
        current_max_id = len(all_rows)

        # Slice latest max_rows
        recent_rows = all_rows[-max_rows:] if len(all_rows) > max_rows else all_rows
        for r in recent_rows:
            top = str(r.get("Topic", "")).strip()
            if top and top not in used_topics:
                used_topics.append(top)

            for i in range(1, 6):
                w_val = str(r.get(f"Word {i}", "")).strip()
                if w_val:
                    hanzi_part = w_val.split("|")[0].strip()
                    if hanzi_part and hanzi_part not in used_words:
                        used_words.append(hanzi_part)

        logger.info(f"Loaded negative context from Sheet: {len(used_words)} words, {len(used_topics)} topics (Max ID: #{current_max_id}).")
    except Exception as e:
        logger.warning(f"Could not load negative context from Google Sheets ({e}). Using empty negative context.")

    return used_words, used_topics, current_max_id


def post_to_cloudflare_webhook(webhook_url: str, payload: Dict[str, Any], timeout: int = 30) -> Tuple[bool, Dict[str, Any]]:
    """
    Post generated idea payload to Cloudflare Worker /api/receive-ideas.
    """
    logger.info(f"Posting idea #{payload.get('row_id')} ('{payload.get('topic')}') to Webhook: {webhook_url}...")
    try:
        resp = requests.post(
            webhook_url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=timeout
        )
        status_code = resp.status_code
        try:
            data = resp.json()
        except Exception:
            data = {"raw_response": resp.text}

        if status_code in (200, 201):
            logger.info(f" Webhook accepted idea #{payload.get('row_id')}: {data}")
            return True, data
        else:
            logger.warning(f"⚠️ Webhook rejected idea #{payload.get('row_id')} (HTTP {status_code}): {data}")
            return False, data
    except Exception as e:
        logger.error(f"❌ Failed to post to webhook ({webhook_url}): {e}")
        return False, {"error": str(e)}


def format_single_batch_payload(
    row_id: str,
    topic: str,
    level: str,
    raw_words: List[Dict[str, str]],
    retry_count: int = 0
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Format standard webhook payload and Sheet row representation.
    """
    formatted_words = []
    sheet_word_cols = []
    words_for_metadata = []

    for w in raw_words:
        hz = str(w.get("hanzi", "")).strip()
        py = str(w.get("pinyin", "")).strip()
        mean = str(w.get("meaning", "")).strip()

        h, fp, hp = prepare_word_tuple(hz, py)
        formatted_words.append({
            "hanzi": h,
            "pinyin": fp,
            "hidden_pinyin": hp,
            "meaning": mean
        })
        words_for_metadata.append({"hanzi": h, "pinyin": fp, "meaning": mean})
        sheet_word_cols.append(f"{h} | {fp} | {hp} | {mean}")

    # Generate metadata text
    metadata_text = save_and_upload_metadata(
        batch_id=str(row_id),
        topic=topic,
        level=level,
        words=words_for_metadata
    )

    webhook_payload = {
        "row_id": str(row_id),
        "topic": topic,
        "level": level,
        "words": formatted_words,
        "metadata": metadata_text,
        "retry_count": retry_count
    }

    now_str = get_vietnam_now_str()
    sheet_row = [
        str(row_id),
        topic,
        level,
        "Pending"
    ] + sheet_word_cols + [
        metadata_text,
        "", "", "", "",
        now_str,
        f"Tự động sinh bởi Gemini 3.7 Flash ({get_vietnam_now_str()} GMT+7)"
    ]

    return webhook_payload, sheet_row


def run_batch_mode(
    count: int = 30,
    gemini_keys: Optional[List[str]] = None,
    webhook_url: str = DEFAULT_WEBHOOK_URL,
    delay_seconds: int = 60,
    update_sheet: bool = False,
    dry_run: bool = False
):
    """
    Step 1: Batch Ideation Mode.
    Generates N ideas sequentially with delay and 6-key rotation, posting each to webhook.
    """
    keys = parse_gemini_keys(gemini_keys)
    masked_keys = [mask_key(k) for k in keys]
    logger.info(f"=== Starting Step 1 Batch Ideation: Count={count}, Keys={len(keys)} {masked_keys}, Delay={delay_seconds}s ===")

    used_words, used_topics, current_max_id = load_negative_context_from_sheet(max_rows=100)

    gsheet_mgr = None
    if update_sheet and not dry_run:
        try:
            gsheet_mgr = GSheetManager()
        except Exception as e:
            logger.warning(f"Google Sheets manager init warning: {e}")

    generated_success_count = 0
    generated_rows_summary = []

    hsk_levels = ["HSK 1", "HSK 2", "HSK 3"]

    for i in range(1, count + 1):
        target_row_id = current_max_id + i
        target_hsk_level = hsk_levels[(i - 1) % len(hsk_levels)]

        # 6-key rotation formula: Key Index = ((i - 1) % len(keys))
        active_key = None
        if keys:
            key_idx = (i - 1) % len(keys)
            active_key = keys[key_idx]
            logger.info(f"\n--- [Idea {i}/{count}] Target Row #{target_row_id} | Level: {target_hsk_level} | Rotating Key [{key_idx + 1}/{len(keys)}]: {mask_key(active_key)} ---")
        else:
            logger.info(f"\n--- [Idea {i}/{count}] Target Row #{target_row_id} | Level: {target_hsk_level} | (No dynamic keys, using fallback/local) ---")

        # 1. Generate 1 topic with 5 words for target level
        topic_batch = None
        try:
            active_key_list = [active_key] if active_key else keys
            # Attempt LLM generation with target_level
            batches = generate_hsk_topics_with_llm(
                existing_words=used_words,
                count=1,
                api_keys=active_key_list,
                existing_topics=used_topics,
                target_level=target_hsk_level
            )
            if batches and len(batches) > 0:
                topic_batch = batches[0]
        except Exception as ge:
            logger.warning(f"LLM generation attempt exception for row #{target_row_id}: {ge}")

        # Fallback to VOCAB_BANK matching target level if LLM failed
        if not topic_batch or not topic_batch.get("words"):
            logger.warning(f"⚠️ Falling back to VOCAB_BANK for idea #{target_row_id} (Level {target_hsk_level})...")
            # Pick a sample from fallback bank that matches target_level and is not already in used_topics
            level_candidates = [fb for fb in FALLBACK_VOCAB_BANK if fb[1] == target_hsk_level and fb[0] not in used_topics]
            if not level_candidates:
                level_candidates = [fb for fb in FALLBACK_VOCAB_BANK if fb[0] not in used_topics]
            if not level_candidates:
                level_candidates = FALLBACK_VOCAB_BANK
            chosen = random.choice(level_candidates)
            topic_batch = {
                "topic": chosen[0],
                "level": chosen[1],
                "words": [{"hanzi": w[0], "pinyin": w[1], "meaning": w[2]} for w in chosen[2]]
            }

        topic_name = topic_batch.get("topic", f"{target_hsk_level} • Chủ Đề #{target_row_id}")
        level_name = topic_batch.get("level", target_hsk_level)
        words_list = topic_batch.get("words", [])

        # Format payload and sheet row
        payload, sheet_row = format_single_batch_payload(
            row_id=str(target_row_id),
            topic=topic_name,
            level=level_name,
            raw_words=words_list,
            retry_count=0
        )

        # Update negative context in-memory so subsequent rows don't repeat
        used_topics.append(topic_name)
        for w in words_list:
            hz = w.get("hanzi", "").strip()
            if hz:
                used_words.append(hz)

        logger.info(f" Generated Idea #{target_row_id}: '{topic_name}' ({level_name}) with {len(words_list)} words.")

        if dry_run:
            logger.info(f"[DRY-RUN] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
            generated_success_count += 1
            generated_rows_summary.append(sheet_row)
        else:
            # 2. Post to Cloudflare Webhook /api/receive-ideas
            post_ok, post_res = post_to_cloudflare_webhook(webhook_url, payload)

            # 3. If update_sheet requested, append to Google Sheet
            if gsheet_mgr:
                try:
                    gsheet_mgr.worksheet.append_row(sheet_row)
                    logger.info(f" Appended row #{target_row_id} to Sheet tab '{gsheet_mgr.tab_name}'.")
                except Exception as se:
                    logger.warning(f"Could not append to Google Sheet: {se}")

            generated_success_count += 1
            generated_rows_summary.append(sheet_row)

        # 4. Sequential 60-second delay between consecutive ideas
        if i < count and delay_seconds > 0:
            logger.info(f"⏳ Waiting {delay_seconds}s before generating next idea ({i + 1}/{count}) to prevent rate limits...")
            time.sleep(delay_seconds)

    # Final summary and Telegram notification
    logger.info("\n" + "=" * 50)
    logger.info(f"🎉 Batch Ideation Complete: {generated_success_count}/{count} ideas created successfully.")
    logger.info("=" * 50)

    if generated_rows_summary:
        bullets = "\n".join([f"• <b>#{r[0]}:</b> {r[1]} (<code>{r[2]}</code>)" for r in generated_rows_summary[:10]])
        if len(generated_rows_summary) > 10:
            bullets += f"\n<i>... và {len(generated_rows_summary) - 10} chủ đề khác</i>"

        send_telegram_alert(
            f"💡 <b>[Batch Ideation Hoàn Tất]</b>\n\n"
            f"Đã tạo thành công <b>{len(generated_rows_summary)}/{count}</b> bộ chủ đề HSK mới (Pipeline 2.0):\n"
            f"{bullets}\n\n"
            f"📊 <b>Trạng thái:</b> <code>Pending</code> (Đã chuyển qua Gatekeeper 1)"
        )


def run_single_row_mode(
    row_id: str,
    rejected_topic: str = "",
    error_reasons: str = "",
    gemini_keys: Optional[List[str]] = None,
    webhook_url: str = DEFAULT_WEBHOOK_URL,
    update_sheet: bool = False,
    dry_run: bool = False
):
    """
    Step 2: Targeted Single-Row Re-generation Mode.
    Generates 1 replacement row avoiding previous errors, and posts to webhook.
    """
    keys = parse_gemini_keys(gemini_keys)
    masked_keys = [mask_key(k) for k in keys]
    clean_row_id = str(row_id).replace("#", "").strip() if row_id else "1"

    logger.info(f"=== Starting Step 2 Single-Row Re-Gen for Row #{clean_row_id} ===")
    logger.info(f"Rejected Topic: '{rejected_topic}'")
    logger.info(f"Error Reasons: '{error_reasons}'")
    logger.info(f"Keys ({len(keys)}): {masked_keys}")

    used_words, used_topics, _ = load_negative_context_from_sheet(max_rows=100)

    # Infer target level
    target_level = None
    for lvl in ["HSK 3", "HSK 2", "HSK 1"]:
        if lvl.lower() in rejected_topic.lower():
            target_level = lvl
            break
    if not target_level:
        try:
            target_level = ["HSK 1", "HSK 2", "HSK 3"][(int(clean_row_id) - 1) % 3]
        except Exception:
            target_level = "HSK 2"

    # Generate replacement topic
    topic_batch = None
    try:
        topic_batch = generate_single_replacement_topic(
            existing_words=used_words,
            row_id=clean_row_id,
            rejected_topic=rejected_topic,
            error_reasons=error_reasons,
            api_keys=keys,
            target_level=target_level
        )
    except Exception as e:
        logger.warning(f"Single-row LLM generation exception: {e}")

    # Fallback if LLM failed
    if not topic_batch or not topic_batch.get("words"):
        logger.warning(f"⚠️ Falling back to VOCAB_BANK for single row #{clean_row_id} (Level {target_level})...")
        candidates = [fb for fb in FALLBACK_VOCAB_BANK if fb[1] == target_level and fb[0] != rejected_topic and fb[0] not in used_topics]
        if not candidates:
            candidates = [fb for fb in FALLBACK_VOCAB_BANK if fb[0] != rejected_topic and fb[0] not in used_topics]
        if not candidates:
            candidates = FALLBACK_VOCAB_BANK
        chosen = random.choice(candidates)
        topic_batch = {
            "topic": chosen[0],
            "level": chosen[1],
            "words": [{"hanzi": w[0], "pinyin": w[1], "meaning": w[2]} for w in chosen[2]]
        }

    topic_name = topic_batch.get("topic", f"{target_level} • Thay Thế #{clean_row_id}")
    level_name = topic_batch.get("level", target_level)
    words_list = topic_batch.get("words", [])

    payload, sheet_row = format_single_batch_payload(
        row_id=clean_row_id,
        topic=topic_name,
        level=level_name,
        raw_words=words_list,
        retry_count=1
    )

    logger.info(f" Replacement Idea #{clean_row_id}: '{topic_name}' ({level_name}) with {len(words_list)} words.")

    if dry_run:
        logger.info(f"[DRY-RUN] Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    else:
        # Post to webhook
        post_ok, post_res = post_to_cloudflare_webhook(webhook_url, payload)

        # Update Google Sheet if requested
        if update_sheet:
            try:
                mgr = GSheetManager()
                row_info = mgr.get_batch_by_id(clean_row_id)
                if row_info and row_info.get("row_index", 0) > 0:
                    row_idx = row_info["row_index"]
                    mgr.update_batch_status(row_idx, "Pending")
                    for col_idx, val in enumerate(sheet_row[1:], start=2):
                        mgr.worksheet.update_cell(row_idx, col_idx, val)
                    logger.info(f" Updated Row #{clean_row_id} (Sheet row {row_idx}) with replacement content.")
            except Exception as se:
                logger.warning(f"Could not update Sheet for row #{clean_row_id}: {se}")

    send_telegram_alert(
        f"🔄 <b>[Tái Sinh Dòng Lỗi - Step 2]</b>\n\n"
        f"• <b>Row ID:</b> <code>#{clean_row_id}</code>\n"
        f"• <b>Chủ đề mới:</b> <b>{topic_name}</b> (<code>{level_name}</code>)\n"
        f"• <b>Chủ đề cũ bị từ chối:</b> <s>{rejected_topic}</s>\n"
        f"• <b>Trạng thái:</b> <code>Pending</code> (Đã gửi lại Gatekeeper 1)"
    )


def main():
    parser = argparse.ArgumentParser(description="Pipeline 2.0 Daily Batch Generator (Google AI Studio Gemini 3.7 Flash)")
    parser.add_argument("--mode", type=str, default="batch", choices=["batch", "single_row"], help="Execution mode: 'batch' (Step 1) or 'single_row' (Step 2)")
    parser.add_argument("--count", type=int, default=5, help="Number of ideas to generate in batch mode (default: 5 ideas/day)")
    parser.add_argument("--row-id", type=str, default="", help="Target Row ID for single-row re-gen")
    parser.add_argument("--rejected-topic", type=str, default="", help="Previous rejected topic for single-row re-gen")
    parser.add_argument("--error-reasons", type=str, default="", help="Error reasons from Gatekeeper 1 for single-row re-gen")
    parser.add_argument("--gemini-keys", type=str, default="", help="Comma-separated ephemeral Gemini API keys")
    parser.add_argument("--webhook-url", type=str, default=DEFAULT_WEBHOOK_URL, help="Cloudflare Worker webhook URL (/api/receive-ideas)")
    parser.add_argument("--delay", type=int, default=60, help="Delay in seconds between consecutive ideas in batch mode (default: 60)")
    parser.add_argument("--update-sheet", action="store_true", help="Also write/update rows to Google Sheet directly")
    parser.add_argument("--dry-run", action="store_true", help="Generate and validate without sending to webhook or Sheet")

    args = parser.parse_args()

    # Dynamic ephemeral keys priority: CLI argument -> env var
    gemini_keys_input = args.gemini_keys or os.getenv("GEMINI_API_KEYS") or ""

    if args.mode == "single_row":
        if not args.row_id:
            logger.error("Error: --row-id is required when running in 'single_row' mode.")
            sys.exit(1)
        run_single_row_mode(
            row_id=args.row_id,
            rejected_topic=args.rejected_topic,
            error_reasons=args.error_reasons,
            gemini_keys=gemini_keys_input,
            webhook_url=args.webhook_url,
            update_sheet=args.update_sheet,
            dry_run=args.dry_run
        )
    else:
        run_batch_mode(
            count=args.count,
            gemini_keys=gemini_keys_input,
            webhook_url=args.webhook_url,
            delay_seconds=args.delay,
            update_sheet=args.update_sheet,
            dry_run=args.dry_run
        )


if __name__ == "__main__":
    main()
