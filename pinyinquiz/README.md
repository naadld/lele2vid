# 🎬 LeLeHocTiengTrung Pinyin Quiz - Docker Container Hub

Phân hệ tự động hóa 100% quy trình sản xuất video ngắn TikTok / Shorts / Reels (tỷ lệ 9:16) luyện tập Pinyin & Chữ Hán tiếng Trung, được đóng gói hoàn toàn trong **Docker Container** để cô lập hoàn toàn môi trường và không ảnh hưởng đến hệ điều hành VPS / Linux local.

---

## 📦 Kiến Trúc Đóng Gói Docker Container

- **Docker Image:** `lelehoctiengtrung-pinyinquiz:latest`
- **Môi trường:** Python 3.12, FFmpeg, Cairo, Pango, Manim Engine, Fonts Noto CJK, Edge TTS AI, Google APIs.
- **Dữ liệu & Cấu hình:** Được mount trực tiếp qua volume host:
  - `./output`: Nhận video hoàn thiện (`.mp4`), metadata (`.txt`), cache Manim.
  - `./configs`: Chứa `service_account.json` và `oauth_credentials.json` để quản trị quyền truy cập Google Sheets & Google Drive.
  - `./assets`: Chứa hình nền video, logo kênh, âm thanh hiệu ứng.
  - `./data`: Dữ liệu từ vựng mẫu dự phòng.
- **Bản lưu trữ mã nguồn gốc (Backup Archive):**
  - Lưu tại: `/media/vpsg16gb/Media/HaRiSync/pinyinquiz_code_archive_20260818_070316.zip`

---

## 🚀 Hướng Dẫn Vận Hành & Lệnh Kích Hoạt

Tại thư mục:
```bash
cd /media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz
```

### 1. Kích hoạt sinh ý tưởng (Ideation)
Tạo 5 bộ chủ đề từ vựng HSK & Metadata mới vào Google Sheets (Status `Pending`):
```bash
./run_ideation.sh
# Hoặc:
./run.sh ideation
```

### 2. Kích hoạt kết xuất video & Upload Drive (Video Gen)
Quét toàn bộ hàng `Pending` trên Google Sheets, render video chuẩn TikTok 1080p60 và upload lên Google Drive:
```bash
./run_videogen.sh
# Hoặc:
./run.sh videogen
```

### 3. Render video một hàng cụ thể theo ID
Ví dụ chỉ render riêng hàng `#3`:
```bash
./run.sh row 3
```

### 4. Kiểm tra render mẫu (Sample Test)
```bash
# Render mẫu chất lượng cao 1080p60:
./run.sh sample

# Render mẫu siêu tốc 480p preview:
./run.sh sample-fast
```

### 5. Quản trị Container nâng cao
```bash
# Build lại Docker image:
./run.sh build

# Mở bash terminal bên trong container:
./run.sh shell
```

---

## 📁 Cấu Trúc Thư Mục Tinh Gọn Hiện Tại

```
/media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz/
├── Dockerfile                  # Cấu hình đóng gói container độc lập
├── docker-compose.yml          # Khởi chạy các service ideation & videogen
├── entrypoint.sh               # Entrypoint điều khiển tác vụ trong container
├── run.sh                      # Trình điều khiển CLI tổng hợp
├── run_ideation.sh             # File kích hoạt nhanh tác vụ Ideation
├── run_videogen.sh             # File kích hoạt nhanh tác vụ Render Video
├── configs/                    # Thư mục chứa credentials Google API
├── assets/                     # Assets hình ảnh và âm thanh video
├── data/                       # Dữ liệu từ vựng mẫu
├── output/                     # Thư mục xuất video (.mp4) và metadata (.txt)
└── README.md                   # Hướng dẫn này
```
