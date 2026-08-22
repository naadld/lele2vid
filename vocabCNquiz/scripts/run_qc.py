import os
import sys
import argparse
import logging

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.gsheet_manager import GSheetManager
from src.qc_inspector import QCInspector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("QCQC")

def main():
    parser = argparse.ArgumentParser(description="Run Automated QC for VocabVNQuiz.")
    parser.add_argument("--row_id", default="", help="Batch ID to QC")
    args = parser.parse_args()

    gsheet = GSheetManager()
    inspector = QCInspector(gsheet_mgr=gsheet)
    logger.info("QC Inspector initialized for VocabVNquiz.")

if __name__ == "__main__":
    main()
