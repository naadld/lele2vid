#!/usr/bin/env bash
# Trigger Video Generation (Render 1080p60 & Upload to Google Drive)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/run.sh" videogen "$@"
