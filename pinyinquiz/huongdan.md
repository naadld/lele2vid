# 📖 HƯỚNG DẪN VẬN HÀNH PINYIN QUIZ (DOCKER PIPELINE)

Hệ thống tự động hóa sản xuất video ngắn TikTok / Shorts / Reels (tỷ lệ 9:16) cho kênh **Lê Lệ Học Tiếng Trung**, hoạt động 100% bên trong Docker container độc lập và tích hợp trực tiếp **AI LLM từ `vpsg24gb:20130`** cho bước sáng tạo ý tưởng (Ideation).

---

## 📍 Vị Trí Thư Mục

Mở Terminal và chuyển đến thư mục dự án:
```bash
cd /media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz
```

---

## 🤖 Cấu Hình LLM Service
- **LLM Endpoint:** `http://vpsg24gb:20130/v1` (tự động định tuyến qua Tailscale IP `100.79.174.89` bên trong Docker).
- **Mô hình mặc định:** `gemini-2.5-flash` (hoặc `gemini-3.6-flash-high`).
- **Cơ chế hoạt động:** Đọc từ vựng đã có trên Google Sheets để tránh trùng lặp $\rightarrow$ LLM sinh 5 chủ đề HSK mới $\rightarrow$ Tính toán Pinyin ẩn $\rightarrow$ Sinh Metadata SEO $\rightarrow$ Tải lên Google Drive $\rightarrow$ Ghi vào Google Sheets.

---

## 🚀 CÁCH 1: CHẠY LIỀN MẠCH TỪ ĐẦU ĐẾN CUỐI (ALL-IN-ONE PIPELINE)

Chạy lệnh này để hệ thống **tự động làm tất cả trong 1 lượt**:
1. Gọi LLM (`vpsg24gb:20130`) sinh 5 bộ từ vựng HSK 1 - 3 không trùng lặp kèm Metadata đa nền tảng.
2. Ghi 5 dòng mới vào Google Sheets với trạng thái `Pending`.
3. Tự động chuyển tiếp quét và Render toàn bộ video chất lượng cao **1080p60**.
4. Tải video thành phẩm lên Google Drive và cập nhật link vào Google Sheets (`Status: Video`).

```bash
# Cách 1 - Dùng file kích hoạt nhanh:
./run_all.sh

# Cách 2 - Dùng lệnh qua CLI:
./run.sh all
```

---

## 🪜 CÁCH 2: CHẠY RIÊNG BIỆT TỪNG BƯỚC (STEP-BY-STEP)

Nếu anh muốn kiểm tra từ vựng trên Google Sheet trước khi render video, hãy chạy riêng từng bước:

### 🔹 BƯỚC 1: Chỉ chạy Ideation (Gọi LLM sinh từ vựng & Metadata)
Tác vụ này sẽ gọi LLM từ máy `vpsg24gb:20130`, tạo 5 bộ chủ đề HSK mới lạ, tạo file metadata SEO (.txt) tải lên Google Drive và thêm 5 dòng mới vào Google Sheets tab `pinyin` ở trạng thái `Pending`:

```bash
# Cách 1 - Dùng file kích hoạt nhanh:
./run_ideation.sh

# Cách 2 - Dùng lệnh CLI:
./run.sh ideation
```

> 💡 *Sau khi chạy xong Bước 1, anh có thể mở Google Sheet tab `pinyin` để xem, chỉnh sửa nghĩa tiếng Việt hoặc đổi từ nếu muốn.*

---

### 🔹 BƯỚC 2: Chỉ chạy Video Generation (Render & Upload Drive)
Tác vụ này sẽ quét toàn bộ các hàng có trạng thái `Pending` trong Google Sheets, kích hoạt Manim kết xuất video chuẩn TikTok (1080x1920@60fps), lồng ghép tiếng tik đếm ngược, chuông Ding và giọng đọc AI tiếng Trung, sau đó upload lên Google Drive:

```bash
# Cách 1 - Dùng file kích hoạt nhanh:
./run_videogen.sh

# Cách 2 - Dùng lệnh CLI:
./run.sh videogen
```

---

## 🎯 CÁC LỆNH BỔ TRỢ HỮU ÍCH

### 1. Render riêng một hàng cụ thể theo ID
Nếu anh chỉ muốn render lại 1 video duy nhất (ví dụ hàng `#10` vừa sinh từ LLM):
```bash
./run.sh row 10
```

### 2. Render thử nghiệm video mẫu (Không cần kết nối Sheets)
```bash
# Render video mẫu chất lượng cao 1080p60:
./run.sh sample

# Render video mẫu siêu tốc 480p preview (để test visual nhanh):
./run.sh sample-fast
```

### 3. Mở Terminal bên trong Docker Container (Debug)
```bash
./run.sh shell
```

### 4. Build lại Docker Image (Khi có cập nhật hệ thống lớn)
```bash
./run.sh build
```

---

## 📂 NƠI LƯU TRỮ DỮ LIỆU & VIDEO XUẤT RA

- **Video MP4 thành phẩm:** [`output/videos/`](file:///media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz/output/videos)
- **File Metadata (.txt) cho Shorts/TikTok/Reels:** [`output/metadata/`](file:///media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz/output/metadata)
- **Google Sheets quản lý:** [Bảng tính Google Sheets (tab `pinyin`)](https://docs.google.com/spreadsheets/d/1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0/edit)
- **Google Drive lưu trữ video:** Thư mục ID `1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB`
- **Bản lưu trữ mã nguồn gốc:** [`/media/vpsg16gb/Media/HaRiSync/pinyinquiz_code_archive_20260818_073327.zip`](file:///media/vpsg16gb/Media/HaRiSync/pinyinquiz_code_archive_20260818_073327.zip)
