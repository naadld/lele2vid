#!/usr/bin/env bash
# ==============================================================================
# LeLeHocTiengTrung Pinyin Quiz - Docker Execution Script
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="lelehoctiengtrung-pinyinquiz:latest"

# Ensure host output directories exist
mkdir -p "$SCRIPT_DIR/output/videos" "$SCRIPT_DIR/output/metadata" "$SCRIPT_DIR/output/generated_scenes" "$SCRIPT_DIR/output/media"

# Function to check or build Docker image if missing
ensure_image() {
    if [[ "$(docker images -q "$IMAGE_NAME" 2> /dev/null)" == "" ]]; then
        echo "🔨 Docker image '$IMAGE_NAME' not found. Building now..."
        docker compose build
    fi
}

usage() {
    echo "=================================================================="
    echo "🎬 Lê Lệ Học Tiếng Trung - Pinyin Quiz Docker Controller"
    echo "=================================================================="
    echo "Sử dụng: ./run.sh [COMMAND] [ARGS...]"
    echo ""
    echo "Quy trình Liền Mạch:"
    echo "  all            : Chạy liền mạch từ Ideation -> Render Video & Upload GDrive"
    echo ""
    echo "Quy trình Từng Bước:"
    echo "  ideation       : Bước 1: Sinh 5 bộ từ vựng HSK & Metadata mới vào Google Sheets"
    echo "  videogen       : Bước 2: Render tất cả hàng 'Pending' trong Sheet & Upload GDrive (1080p60)"
    echo "  row <ID>       : Render riêng một hàng cụ thể (ví dụ: ./run.sh row 3)"
    echo "  sample         : Render video mẫu 1080p60 để kiểm tra"
    echo "  sample-fast    : Render video mẫu 480p (siêu tốc)"
    echo "  build          : Build lại Docker image"
    echo "  shell          : Mở bash shell bên trong Docker container"
    echo "=================================================================="
}

CMD="${1:-help}"
shift || true

case "$CMD" in
    all|pipeline|full)
        ensure_image
        echo "=================================================================="
        echo "🚀 [BƯỚC 1/2] Đang chạy Ideation (Tạo 5 batch từ vựng vào Google Sheets)..."
        echo "=================================================================="
        docker compose run --rm pinyinquiz ideation
        echo ""
        echo "=================================================================="
        echo "🎬 [BƯỚC 2/2] Đang chạy Video Generation (Render 1080p60 & Upload Drive)..."
        echo "=================================================================="
        docker compose run --rm pinyinquiz video-gen "$@"
        echo ""
        echo "🎉 Hoàn tất 100% toàn bộ quy trình liền mạch (Ideation + Render Video)!"
        ;;
    ideation|batch-gen)
        ensure_image
        echo "🚀 Đang chạy tác vụ Ideation (Tạo 5 batch từ vựng vào Google Sheets)..."
        docker compose run --rm pinyinquiz ideation "$@"
        ;;
    videogen|video-gen|render)
        ensure_image
        echo "🎬 Đang chạy quy trình Render Video 1080p60 & Upload Google Drive..."
        docker compose run --rm pinyinquiz video-gen "$@"
        ;;
    sample)
        ensure_image
        echo "🧪 Đang render video mẫu 1080p60..."
        docker compose run --rm pinyinquiz sample "$@"
        ;;
    sample-fast|test-fast)
        ensure_image
        echo "⚡ Đang render video mẫu 480p siêu tốc..."
        docker compose run --rm pinyinquiz sample-fast "$@"
        ;;
    row)
        ROW_ID="$1"
        shift || true
        if [ -z "$ROW_ID" ]; then
            echo "❌ Vui lòng nhập Row ID (Ví dụ: ./run.sh row 3)"
            exit 1
        fi
        ensure_image
        echo "🎯 Đang render riêng hàng #$ROW_ID..."
        docker compose run --rm pinyinquiz python scripts/run_batch.py --from-sheet --row-id "$ROW_ID" --quality qh --upload-gdrive "$@"
        ;;
    build)
        echo "🔨 Đang build lại Docker image..."
        docker compose build
        echo "✅ Build hoàn tất!"
        ;;
    shell|bash|sh)
        ensure_image
        docker compose run --rm -it pinyinquiz bash
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        ensure_image
        # Pass raw command into docker run
        docker compose run --rm pinyinquiz "$CMD" "$@"
        ;;
esac
