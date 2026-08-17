# 🇨🇳 LELEHOC TIENG TRUNG - CONTENT AUTOMATION HUB

Kho dự án tự động hóa sản xuất nội dung video đa nền tảng (TikTok, YouTube Shorts, Facebook Reels) cho kênh **Lê Lệ Học Tiếng Trung**.

---

## 📂 Cấu Trúc Dự Án (Multi-Module Project)

Dự án được phân chia thành các hạng mục (sub-modules) độc lập:

```
lelehoctiengtrung/
├── pinyinquiz/                 # 🎯 Hạng mục: Video trắc nghiệm Pinyin & Hán tự HSK
│   ├── assets/                 # Backgrounds, logos, sound effects, voice caches
│   ├── configs/                # Cấu hình API, Google Service Account, OAuth 2.0
│   ├── data/                   # Dữ liệu từ vựng mẫu
│   ├── output/                 # Video MP4 xuất bản và cache Manim
│   ├── scripts/                # CLI batch runner, sync Google Sheets & Drive
│   ├── src/                    # Mã nguồn Manim engine, TTS, Pinyin utils
│   ├── tiktok_hsk.py           # Kịch bản Manim test độc lập
│   ├── requirements.txt        # Danh sách thư viện Python cho module
│   └── README.md               # Tài liệu chi tiết module Pinyin Quiz
├── .github/
│   └── workflows/
│       └── daily_render.yml    # GitHub Actions tự động render & upload mỗi ngày
├── .venv/                      # Môi trường ảo Python dùng chung
├── requirements.txt            # Thư viện toàn cục
└── README.md                   # Tài liệu tổng quan dự án
```

---

## 🎯 Danh Sách Hạng Mục

### 1. [`pinyinquiz/`](pinyinquiz/)
- **Mục tiêu**: Tự động tạo video dọc 9:16 (1080x1920) dạng đố vui đoán Pinyin tiếng Trung (5 từ/video) với đồng hồ đếm ngược 5 giây, hiệu ứng âm thanh sống động, chuông ding và phát âm tiếng Trung chuẩn xác bản xứ.
- **Tích hợp**: Google Sheets (tab `pinyin`) và Google Drive (tự động upload & cập nhật link).
- **Xem chi tiết hướng dẫn**: [`pinyinquiz/README.md`](pinyinquiz/README.md)

---

## 🚀 Khởi Chạy Nhanh

```bash
# 1. Kích hoạt môi trường:
source .venv/bin/activate

# 2. Chuyển vào thư mục hạng mục muốn chạy (ví dụ Pinyin Quiz):
cd pinyinquiz

# 3. Chạy render batch từ Google Sheets:
PYTHONPATH=. python scripts/run_batch.py --from-sheet --quality qh --upload-gdrive
```
