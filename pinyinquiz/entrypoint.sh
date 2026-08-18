#!/usr/bin/env bash
set -e

# Change to app directory
cd /app

CMD="${1:-video-gen}"
shift || true

case "$CMD" in
    ideation|generate-batches)
        echo "=========================================================="
        echo "🚀 Running Pinyin Quiz Ideation (Daily Batches Generator)..."
        echo "=========================================================="
        exec python scripts/generate_daily_batches.py "$@"
        ;;
    video-gen|videogen|render)
        echo "=========================================================="
        echo "🎬 Running Pinyin Quiz Video Generation Pipeline (Sheet)..."
        echo "=========================================================="
        exec python scripts/run_batch.py --from-sheet --quality qh --upload-gdrive "$@"
        ;;
    sample)
        echo "=========================================================="
        echo "🧪 Running Pinyin Quiz Sample Video Render (1080p60)..."
        echo "=========================================================="
        exec python scripts/run_batch.py --sample --quality qh "$@"
        ;;
    sample-fast|test-fast)
        echo "=========================================================="
        echo "⚡ Running Pinyin Quiz Fast Sample Render (480p preview)..."
        echo "=========================================================="
        exec python scripts/run_batch.py --sample --quality ql "$@"
        ;;
    test-scene)
        echo "=========================================================="
        echo "🎨 Rendering Standalone Test Scene (tiktok_hsk.py)..."
        echo "=========================================================="
        exec manim -ql tiktok_hsk.py HSKQuiz --media_dir output/media "$@"
        ;;
    python)
        exec python "$@"
        ;;
    bash|sh)
        exec /bin/bash "$@"
        ;;
    *)
        # If user passes custom arguments to run_batch.py or python
        if [[ "$CMD" == --* ]]; then
            exec python scripts/run_batch.py "$CMD" "$@"
        elif [[ "$CMD" == *.py ]]; then
            exec python "$CMD" "$@"
        else
            exec "$CMD" "$@"
        fi
        ;;
esac
