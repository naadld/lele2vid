import os
import sys
import re
import argparse
import logging
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import config
from src.gsheet_manager import GSheetManager
from src.scene_generator import create_scene_file
from src.render_engine import render_scene_file
from src.audio_generator import ensure_bell_sound, ensure_tick_sound
from src.gdrive_uploader import GDriveUploader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("BatchRunner")

def sanitize_filename(name: str) -> str:
    """Sanitize string for safe cross-platform filename."""
    s = re.sub(r'[/\\:*?"<>|]', '_', name)
    return s.strip()

def run_batch_job(from_sheet: bool = True, target_id: str = None, sample: bool = False, quality: str = "qh", upload_gdrive: bool = False):
    """
    Main batch processing function.
    """
    ensure_bell_sound()
    ensure_tick_sound()

    batches_to_process = []
    gsheet_mgr = None
    gdrive_uploader = None

    if upload_gdrive:
        try:
            gdrive_uploader = GDriveUploader()
        except Exception as e:
            logger.warning(f"Could not initialize GDriveUploader: {e}")

    if from_sheet:
        logger.info("Connecting to Google Sheets...")
        gsheet_mgr = GSheetManager()
        all_pending = gsheet_mgr.get_pending_batches()
        if target_id:
            batches_to_process = [b for b in all_pending if str(b["id"]) == str(target_id)]
        else:
            batches_to_process = all_pending
    elif sample:
        batches_to_process = [{
            "row_index": 0,
            "id": "sample_hsk12",
            "topic": "HSK 1-2 • ĐOÁN PINYIN",
            "level": "HSK 1-2",
            "words": [
                {"hanzi": "苹果", "pinyin": "píng guǒ", "hidden_pinyin": "p _ _ _   g _ _", "meaning": "Quả táo"},
                {"hanzi": "米饭", "pinyin": "mǐ fàn", "hidden_pinyin": "m _   f _ _", "meaning": "Cơm"},
                {"hanzi": "面包", "pinyin": "miàn bāo", "hidden_pinyin": "m _ _ _   b _ _", "meaning": "Bánh mì"},
                {"hanzi": "喝水", "pinyin": "hē shuǐ", "hidden_pinyin": "h _   s _ _ _", "meaning": "Uống nước"},
                {"hanzi": "吃饭", "pinyin": "chī fàn", "hidden_pinyin": "c _ _   f _ _", "meaning": "Ăn cơm"}
            ]
        }]

    if not batches_to_process:
        logger.info("No batches found to process.")
        return

    logger.info(f"Found {len(batches_to_process)} batches to process.")

    for batch in batches_to_process:
        row_id = batch["id"]
        topic = batch["topic"]
        level = batch.get("level", "HSK 1-2")
        words = batch["words"]
        row_index = batch.get("row_index", 0)

        logger.info("\n" + "=" * 50)
        logger.info(f"Processing Batch ID [{row_id}]: {topic}")
        logger.info(f"Total Words: {len(words)}")
        logger.info(f"Quality: {quality}")
        logger.info("=" * 50)

        if gsheet_mgr and row_index > 0:
            gsheet_mgr.update_batch_status(row_index, "In Progress")

        # 1. Generate scene python file
        scene_file, scene_name = create_scene_file(batch)
        logger.info(f"Generated scene: {scene_name} at {scene_file}")

        # 2. Render Video with Manim
        clean_topic_name = sanitize_filename(topic)
        final_video_name = f"#{row_id}.{clean_topic_name}.mp4"
        custom_video_path = os.path.join(config.output_videos_dir, final_video_name)

        success, video_path = render_scene_file(
            scene_file,
            scene_name,
            quality=quality,
            custom_output_name=final_video_name
        )

        if success and video_path:
            logger.info(f"Video rendered successfully: {video_path}")
            
            gdrive_link = ""
            if gdrive_uploader:
                try:
                    gdrive_link = gdrive_uploader.upload_file(video_path, final_video_name) or ""
                except Exception as ue:
                    logger.error(f"GDrive upload error: {ue}")

            if gsheet_mgr and row_index > 0:
                # Update status to 'Video' as requested by user
                gsheet_mgr.update_batch_status(
                    row_index=row_index,
                    status="Video",
                    video_file=final_video_name,
                    gdrive_link=gdrive_link
                )

            logger.info(f" Batch [{row_id}] finished successfully -> {video_path}")
        else:
            logger.error(f"❌ Failed to render batch [{row_id}]")
            if gsheet_mgr and row_index > 0:
                gsheet_mgr.update_batch_status(row_index, "Failed")

def main():
    parser = argparse.ArgumentParser(description="lelehoctiengtrung_pinyin Batch Runner")
    parser.add_argument("--from-sheet", action="store_true", help="Fetch batches from Google Sheets")
    parser.add_argument("--sample", action="store_true", help="Run with built-in sample batch")
    parser.add_argument("--row-id", type=str, default=None, help="Process a specific row ID from Sheet")
    parser.add_argument("--quality", type=str, default="qh", choices=["ql", "qm", "qh", "qk"], help="Render quality (default: qh 1080p60)")
    parser.add_argument("--upload-gdrive", action="store_true", help="Upload rendered video to Google Drive")
    
    args = parser.parse_args()
    
    if not args.from_sheet and not args.sample and not args.row_id:
        args.from_sheet = True

    run_batch_job(
        from_sheet=args.from_sheet or bool(args.row_id),
        target_id=args.row_id,
        sample=args.sample,
        quality=args.quality,
        upload_gdrive=args.upload_gdrive
    )

if __name__ == "__main__":
    main()
