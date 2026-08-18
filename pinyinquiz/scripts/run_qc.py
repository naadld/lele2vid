import os
import sys
import json
import logging
import argparse
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import config
from src.gsheet_manager import GSheetManager
from src.qc_inspector import QCInspector, download_video_file

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AutoQCRunner")

def send_telegram_qc_alert(text: str):
    """Send Auto-QC notification to Telegram bot."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or "8974080727:AAFiyOQzfadrZ8EF_IhYrNnwsy-9BTnsYis"
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip() or "6800539169"

    if not (bot_token and chat_id):
        logger.info("Telegram notification skipped (bot token or chat ID missing).")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        import requests
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        res = requests.post(url, json=data, timeout=20)
        if res.status_code == 200:
            logger.info("Sent Auto-QC notification to Telegram.")
        else:
            logger.warning(f"Failed to send Telegram alert: {res.status_code} - {res.text}")
    except Exception as e:
        logger.warning(f"Telegram notification error: {e}")

def run_auto_qc(target_row_id: str = None):
    logger.info("=== Starting Auto-QC Gatekeeper Pipeline ===")
    
    gsheet_mgr = GSheetManager()
    inspector = QCInspector()

    # Find rows with Status == 'Video'
    all_rows = gsheet_mgr.get_all_rows()
    video_batches = []

    for idx, r in enumerate(all_rows, start=2):
        status = str(r.get("Status", "")).strip()
        if status.lower() == "video":
            row_id = str(r.get("#", idx))
            if target_row_id and row_id != target_row_id:
                continue

            words = []
            for w_idx in range(1, 6):
                w_val = str(r.get(f"Word {w_idx}", "")).strip()
                if w_val:
                    parts = [p.strip() for p in w_val.split("|")]
                    words.append({
                        "hanzi": parts[0] if len(parts) > 0 else "",
                        "pinyin": parts[1] if len(parts) > 1 else "",
                        "hidden_pinyin": parts[2] if len(parts) > 2 else "",
                        "meaning": parts[3] if len(parts) > 3 else parts[0]
                    })

            video_batches.append({
                "row_index": idx,
                "id": row_id,
                "topic": r.get("Topic", "HSK 1-2"),
                "level": r.get("Level", "HSK 1-2"),
                "words": words,
                "video_url": r.get("Video", ""),
                "metadata": r.get("metadata", ""),
                "notes": r.get("Notes", "")
            })

    if not video_batches:
        logger.info("No batches found with status 'Video'. QC complete.")
        return

    logger.info(f"Found {len(video_batches)} batch(es) with status 'Video' to inspect.")
    tmp_qc_dir = os.path.join(config.base_dir, "output", "qc_temp")
    os.makedirs(tmp_qc_dir, exist_ok=True)

    passed_count = 0
    failed_count = 0

    for batch in video_batches:
        row_id = batch["id"]
        topic = batch["topic"]
        level = batch["level"]
        row_idx = batch["row_index"]
        video_url = batch["video_url"]

        logger.info("\n" + "=" * 50)
        logger.info(f"Checking Batch #{row_id}: {topic} ({level})")
        logger.info(f"Video URL: {video_url}")
        logger.info("=" * 50)

        if not video_url:
            logger.warning(f"Batch #{row_id} has status 'Video' but no Video URL. Reverting to Pending.")
            gsheet_mgr.update_batch_status(row_idx, "Pending")
            continue

        # 1. Download video file
        local_video_name = f"qc_batch_{row_id}.mp4"
        local_video_path = os.path.join(tmp_qc_dir, local_video_name)

        download_ok = download_video_file(video_url, local_video_path)
        if not download_ok or not os.path.exists(local_video_path):
            logger.error(f"Could not download video for Batch #{row_id}. Skipping.")
            continue

        # 2. Run QC Inspection
        result = inspector.inspect_batch(batch, local_video_path)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if result["passed"]:
            logger.info(f"✨ Batch #{row_id} PASSED all QC checks! Changing Status to 'Ready'.")
            passed_count += 1
            
            # Update Sheet status to 'Ready'
            gsheet_mgr.worksheet.update_cell(row_idx, 4, "Ready")
            
            # Update Notes column (Col 16: P)
            try:
                gsheet_mgr.worksheet.update_cell(row_idx, 16, f"[Auto-QC Passed lúc {now_str}]")
            except Exception as e:
                logger.warning(f"Could not update Notes: {e}")

            # Notify Telegram
            tg_msg = (
                f"🤖 <b>[Auto-QC Gatekeeper] Đã Duyệt Tự Động Thành Công!</b>\n\n"
                f"🎬 <b>Batch #{row_id}:</b> <b>{topic}</b> (<code>{level}</code>)\n"
                f"📊 <b>Trạng thái:</b> <code>Video ➔ Ready</code> (Sẵn sàng đăng)\n"
                f"✅ <b>Chi tiết kiểm tra:</b>\n"
                f"• Chữ Hán Giản thể chuẩn HSK: 100%\n"
                f"• Khung hình & Pinyin an toàn: Không tràn viền\n"
                f"• Định dạng video: {result['details'].get('width', 1080)}x{result['details'].get('height', 1920)} ({result['details'].get('duration_sec', 0)}s)\n\n"
                f"<i>Video sẽ tự động được Buffer đăng lên YouTube, TikTok, Facebook Reels lúc 07:00 / 13:00!</i>"
            )
            send_telegram_qc_alert(tg_msg)

        else:
            errors_str = " | ".join(result["errors"])
            logger.warning(f"❌ Batch #{row_id} FAILED QC checks: {errors_str}. Reverting Status to 'Pending'.")
            failed_count += 1

            # Clear video link and revert status to 'Pending'
            gsheet_mgr.worksheet.update_cell(row_idx, 4, "Pending")
            try:
                gsheet_mgr.worksheet.update_cell(row_idx, 11, "") # Clear Video Link
                gsheet_mgr.worksheet.update_cell(row_idx, 16, f"[Auto-QC Lỗi: {errors_str[:150]} lúc {now_str}]")
            except Exception as e:
                logger.warning(f"Could not update cell: {e}")

            # Notify Telegram
            error_bullets = "\n".join([f"• {e}" for e in result["errors"]])
            tg_msg = (
                f"⚠️ <b>[Auto-QC Gatekeeper] Phát Hiện Video Lỗi:</b>\n\n"
                f"🎬 <b>Batch #{row_id}:</b> <b>{topic}</b> (<code>{level}</code>)\n"
                f"❌ <b>Lý do không đạt chuẩn:</b>\n{error_bullets}\n\n"
                f"🔄 <b>Hành động:</b> Đã tự động chuyển về <code>Pending</code> để render lại trong ca tiếp theo."
            )
            send_telegram_qc_alert(tg_msg)

        # Cleanup local downloaded video
        if os.path.exists(local_video_path):
            try:
                os.remove(local_video_path)
            except Exception:
                pass

    logger.info("\n" + "=" * 50)
    logger.info(f"Auto-QC Summary: {passed_count} Passed (Ready), {failed_count} Failed (Pending).")
    logger.info("=" * 50)

def main():
    parser = argparse.ArgumentParser(description="Auto-QC Gatekeeper Runner")
    parser.add_argument("--row-id", type=str, default=None, help="Inspect a specific batch ID")
    args = parser.parse_args()

    run_auto_qc(target_row_id=args.row_id)

if __name__ == "__main__":
    main()
