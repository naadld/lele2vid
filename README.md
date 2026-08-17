# LeLeHocTiengTrung Pinyin Quiz Video Pipeline 🎬

Hệ thống tự động hóa 100% quy trình sản xuất video ngắn TikTok / Shorts / Reels (tỷ lệ 9:16) luyện tập Pinyin & Chữ Hán tiếng Trung từ Google Sheets.

---

## 🌟 Tính Năng Nổi Bật

1. **Giao Diện Chuẩn TikTok & Visual Đẹp Mắt**:
   - Thẻ câu đố kính mờ sang trọng (**Glassmorphism Card**).
   - Chữ tiếng Trung to rõ, font chuẩn đẹp.
   - Nghĩa tiếng Việt font Arial rõ nét.
   - Pinyin ẩn hiển thị chữ cái đầu của từng âm tiết (`p _ _ _   g _ _`).
   - Đồng hồ đếm ngược 5 giây (`TIME 5..4..3..2..1`) kết hợp thanh chạy ngang co dần.

2. **Âm Thanh & Giọng Đọc Kỹ Thuật Số Bản Xứ**:
   - Âm thanh đếm ngược `tik... tik... tik...` theo từng giây.
   - Chuông Ding trong trẻo khi hết giờ.
   - **Giọng đọc tiếng Trung tự động (TTS Microsoft Edge)** phát âm chuẩn xác từng từ vựng khi hiện đáp án.

3. **Tự Động Hóa 100% với Google Sheets & Google Drive**:
   - **02:00 GMT+7**: Script tự động tạo 5 dòng từ vựng HSK mới không trùng lặp, đặt trạng thái `Pending`.
   - **03:00 GMT+7**: **GitHub Actions** tự động kích hoạt, kết xuất video 1080p60, upload lên Google Drive folder `1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB`, đặt tên `#số dòng.topic.mp4`, cập nhật trạng thái `Video` và lưu link trên Google Sheets.

---

## 📁 Cấu Trúc Dự Án

```
lelehoctiengtrung_pinyin/
├── .github/workflows/
│   └── daily_render.yml          # GitHub Actions tự động render & upload mỗi ngày 03:00 GMT+7
├── assets/
│   ├── images/
│   │   ├── background.jpg        # Hình nền vũ trụ điện ảnh độ phân giải cao
│   │   └── logo.png              # Avatar mascot lelehoctiengtrung
│   └── audio/
│       ├── ding.mp3              # Chuông ding báo đáp án
│       ├── tick.mp3              # Âm thanh tích tắc đếm ngược
│       └── words/                # Cache giọng đọc phát âm tiếng Trung
├── src/
│   ├── config.py                 # Cấu hình dự án & đường dẫn
│   ├── pinyin_utils.py           # Chuyển đổi Hanzi -> Pinyin & mặt nạ gạch dưới
│   ├── gsheet_manager.py         # Quản lý đọc/ghi Google Sheets tab 'pinyin'
│   ├── gdrive_uploader.py        # Upload video lên Google Drive folder
│   ├── scene_generator.py        # Trình sinh mã kịch bản Manim động
│   ├── render_engine.py          # Wrapper điều khiển Manim CLI
│   └── audio_generator.py        # Sinh âm thanh & TTS giọng đọc
├── scripts/
│   ├── generate_daily_batches.py # Sinh 5 batch từ vựng mới mỗi ngày (02:00 GMT+7)
│   ├── run_batch.py              # CLI render & upload video hàng loạt
│   └── populate_sample_batches.py# Khởi tạo bảng dữ liệu mẫu
├── tiktok_hsk.py                 # File kịch bản độc lập chạy nhanh
├── requirements.txt              # Danh sách thư viện Python
└── README.md
```

---

## 🚀 Hướng Dẫn Sử Dụng Trên VPS

```bash
cd /media/vpsg16gb/Workspace/lelehoctiengtrung_pinyin

# 1. Kích hoạt môi trường:
source .venv/bin/activate

# 2. Render tất cả hàng 'Pending' trong Google Sheet:
PYTHONPATH=. python scripts/run_batch.py --from-sheet --quality qh --upload-gdrive

# 3. Sinh thêm 5 hàng từ vựng mới vào Google Sheets:
PYTHONPATH=. python scripts/generate_daily_batches.py

# 4. Chạy trực tiếp file kịch bản độc lập:
manim -qh tiktok_hsk.py HSKQuiz --media_dir output/media
```

---

## 🔒 Cài Đặt GitHub Secrets Cho GitHub Actions

Trên GitHub repository `https://github.com/naadld/lele2vid`:
1. Vào **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**.
2. Thêm Secret mới:
   - **Name**: `GCP_SERVICE_ACCOUNT_JSON`
   - **Value**: Dán toàn bộ nội dung JSON của file Service Account.
