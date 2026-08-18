#!/usr/bin/env bash
# Trigger All-in-One Seamless Pipeline (Ideation -> Render Video 1080p60 -> Upload GDrive)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/run.sh" all "$@"
