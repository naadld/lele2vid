#!/usr/bin/env bash
# Trigger Ideation (Generate 5 HSK Batches into Google Sheets)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/run.sh" ideation "$@"
