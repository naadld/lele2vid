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

    video_batches = []

    if target_row_id:
        target_clean = str(target_row_id).replace("#", "").strip()
        batch = gsheet_mgr.get_batch_by_id(target_clean)
        if batch:
            video_batches = [batch]
            logger.info(f"Targeted specific batch #{target_clean}: '{batch.get('topic')}'")
        else:
            logger.warning(f"Could not find batch #{target_clean} on Google Sheets.")
            return
    else:
        video_batches = gsheet_mgr.get_batches_by_status("Video")

    if not video_batches:
        logger.info("No batches found with status 'Video'. QC complete.")
        send_telegram_qc_alert(
            f"ℹ️ <b>[Auto-QC Gatekeeper] Hoàn Tất Quét</b>\n\n"
            f"Hiện không có video nào ở trạng thái <code>Video</code> cần duyệt.\n"
            f"Tất cả video đã ở trạng thái <code>Ready</code> hoặc đang chờ render."
        )
        return

    logger.info(f"Found {len(video_batches)} batch(es) with status 'Video' to inspect.")
    tmp_qc_dir = os.path.join(config.base_dir, "output", "qc_temp")
    os.makedirs(tmp_qc_dir, exist_ok=True)

    passed_count = 0
    failed_count = 0
    skipped_count = 0

    for batch in video_batches:
        row_id = batch["id"]
        topic = batch["topic"]
        level = batch["level"]
        row_idx = batch["row_index"]
        video_url = batch.get("video_url", "")

        logger.info("\n" + "=" * 50)
        logger.info(f"Checking Batch #{row_id} (Row {row_idx}): {topic} ({level})")
        logger.info(f"Video URL: {video_url}")
        logger.info("=" * 50)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not video_url:
            logger.warning(f"Batch #{row_id} has status 'Video' but no Video URL. Skipping.")
            skipped_count += 1
            try:
                gsheet_mgr.worksheet.update_cell(row_idx, 16, f"[Auto-QC: Chưa có link Video lúc {now_str}]")
            except Exception:
                pass
            continue

        # 1. Download video file
        local_video_name = f"qc_batch_{row_id}.mp4"
        local_video_path = os.path.join(tmp_qc_dir, local_video_name)

        download_ok = download_video_file(video_url, local_video_path)
        if not download_ok or not os.path.exists(local_video_path):
            logger.error(f"Could not download video for Batch #{row_id}. Leaving status as 'Video' for retry.")
            skipped_count += 1
            try:
                gsheet_mgr.worksheet.update_cell(row_idx, 16, f"[Auto-QC: Tải video thất bại lúc {now_str}]")
            except Exception:
                pass
            continue

        # 2. Run QC Inspection
        result = inspector.inspect_batch(batch, local_video_path)

        if result["passed"]:
            logger.info(f"✨ Batch #{row_id} PASSED all QC checks! Changing Status to 'Ready'.")
            passed_count += 1
            
            # Update Sheet status to 'Ready' (Col 4: D)
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
                f"• Âm thanh & Khung hình: 1080x1920 9:16 ({result['details'].get('duration_sec', 0)}s, {result['details'].get('fps', 0)} FPS)\n"
                f"• Bố cục nội dung: Chuẩn an toàn 5 từ\n\n"
                f"<i>Video sẽ tự động được Buffer đăng lên YouTube, TikTok, Facebook Reels lúc 07:00 / 13:00!</i>"
            )
            send_telegram_qc_alert(tg_msg)

        else:
            errors_str = " | ".join(result["errors"])
            logger.warning(f"❌ Batch #{row_id} FAILED QC checks: {errors_str}. Changing Status to 'Failed'.")
            failed_count += 1

            # Update status to 'Failed' (KEEP video link intact in Col 11 for manual review)
            gsheet_mgr.worksheet.update_cell(row_idx, 4, "Failed")
            try:
                gsheet_mgr.worksheet.update_cell(row_idx, 16, f"[Auto-QC Lỗi: {errors_str[:150]} lúc {now_str}]")
            except Exception as e:
                logger.warning(f"Could not update cell: {e}")

            # Notify Telegram
            error_bullets = "\n".join([f"• {e}" for e in result["errors"]])
            tg_msg = (
                f"⚠️ <b>[Auto-QC Gatekeeper] Phát Hiện Video Lỗi:</b>\n\n"
                f"🎬 <b>Batch #{row_id}:</b> <b>{topic}</b> (<code>{level}</code>)\n"
                f"❌ <b>Lý do không đạt chuẩn:</b>\n{error_bullets}\n\n"
                f"🔄 <b>Trạng thái:</b> <code>Video ➔ Failed</code> (Link video vẫn được giữ để bạn kiểm tra lại)."
            )
            send_telegram_qc_alert(tg_msg)

        # Cleanup local downloaded video
        if os.path.exists(local_video_path):
            try:
                os.remove(local_video_path)
            except Exception:
                pass

    logger.info("\n" + "=" * 50)
    logger.info(f"Auto-QC Summary: {passed_count} Passed (Ready), {failed_count} Failed (QC_Failed), {skipped_count} Skipped.")
    logger.info("=" * 50)

    # Send summary notification if checked multiple batches
    if len(video_batches) > 1:
        skip_text = f"\n• ⚠️ <b>{skipped_count}</b> video tạm bỏ qua" if skipped_count > 0 else ""
        summary_msg = (
            f"🏁 <b>[Tổng Kết Auto-QC Gatekeeper]</b>\n\n"
            f"📊 Đã quét <b>{len(video_batches)}</b> video:\n"
            f"• ✅ <b>{passed_count}</b> video đạt chuẩn ➔ <code>Ready</code>\n"
            f"• ❌ <b>{failed_count}</b> video lỗi ➔ <code>Failed</code>"
            f"{skip_text}"
        )
        send_telegram_qc_alert(summary_msg)

def main():
    parser = argparse.ArgumentParser(description="Auto-QC Gatekeeper Runner")
    parser.add_argument("--row-id", type=str, default=None, help="Inspect a specific batch ID")
    args = parser.parse_args()

    run_auto_qc(target_row_id=args.row_id)

if __name__ == "__main__":
    main()
