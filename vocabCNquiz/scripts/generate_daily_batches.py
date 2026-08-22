import os
import sys
import time
import json
import logging
import argparse
import requests
from typing import List, Dict, Any

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.gsheet_manager import GSheetManager
from src.llm_client import FALLBACK_VOCAB_BANK

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VocabVNIdeation")

DEFAULT_WEBHOOK_URL = os.getenv("CF_WEBHOOK_URL", "https://lele-vocabvnquiz.hothihuong113.workers.dev/api/receive-ideas")

def send_ideas_to_gatekeeper_webhook(webhook_url: str, ideas_payload: list) -> dict:
    headers = {"Content-Type": "application/json"}
    auth_secret = os.getenv("CF_WEBHOOK_SECRET") or os.getenv("GATEKEEPER_SECRET")
    if auth_secret:
        headers["Authorization"] = f"Bearer {auth_secret}"

    logger.info(f"Connecting to Gatekeeper 1 Webhook: {webhook_url}...")
    res = requests.post(webhook_url, json=ideas_payload, headers=headers, timeout=60)
    if res.status_code == 200:
        return res.json()
    else:
        raise RuntimeError(f"Gatekeeper Webhook Error ({res.status_code}): {res.text}")

def main():
    parser = argparse.ArgumentParser(description="Generate VocabVNQuiz Batches via Gatekeeper 1.")
    parser.add_argument("--count", type=int, default=1, help="Number of batches to generate")
    parser.add_argument("--level", default="HSK 1", help="Target HSK level")
    parser.add_argument("--webhook_url", default=DEFAULT_WEBHOOK_URL, help="Cloudflare Gatekeeper 1 webhook URL")
    args = parser.parse_args()

    gsheet = GSheetManager()
    all_rows = gsheet.get_all_rows()
    target_row = len(all_rows) + 2  # Row number on sheet (1-indexed + header)

    logger.info(f"Target Row on sheet: #{target_row} (Strict Row == # rule)")

    # Construct payload for Gatekeeper 1
    ideas_payload = [{
        "id": str(target_row),
        "target_row": target_row,
        "level": args.level
    }]

    try:
        res = send_ideas_to_gatekeeper_webhook(args.webhook_url, ideas_payload)
        logger.info(f"✅ Gatekeeper 1 Webhook Response: {res}")
    except Exception as e:
        logger.warning(f"⚠️ Webhook execution failed ({e}). Falling back to direct sheet write...")
        # Pick from fallback bank
        candidate = FALLBACK_VOCAB_BANK[0]
        words = [{"hanzi": w[0], "pinyin": w[1], "meaning": w[2]} for w in candidate[2]]
        batch_data = {
            "topic": candidate[0],
            "level": candidate[1],
            "status": "Pending",
            "word_1": f"{words[0]['hanzi']} | {words[0]['pinyin']} | {words[0]['meaning']}",
            "word_2": f"{words[1]['hanzi']} | {words[1]['pinyin']} | {words[1]['meaning']}",
            "word_3": f"{words[2]['hanzi']} | {words[2]['pinyin']} | {words[2]['meaning']}",
            "word_4": f"{words[3]['hanzi']} | {words[3]['pinyin']} | {words[3]['meaning']}",
            "word_5": f"{words[4]['hanzi']} | {words[4]['pinyin']} | {words[4]['meaning']}",
            "notes": "Fallback bank write"
        }
        gsheet.append_or_insert_batch(batch_data, target_row=target_row)
        logger.info(f"Fallback batch written to row #{target_row}")

if __name__ == "__main__":
    main()
