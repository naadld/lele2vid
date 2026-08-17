# ⏰ Hướng Dẫn Setup Scheduled Task Trên Antigravity 2.0 (Máy VPS)

Tài liệu này chứa cấu hình và nội dung Prompt để cài đặt tác vụ tự động sinh 5 bộ ý tưởng từ vựng HSK hàng ngày vào Google Sheets tab `pinyin`.

---

## ⚙️ 1. Thông Tin Cấu Hình Scheduled Task

| Trường (Field) | Giá trị thiết lập |
| :--- | :--- |
| **Task Name** | `LeLe - Daily 5 Pinyin Quiz Batches` |
| **Workspace / Project** | `/media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz` |
| **Schedule (Cron)** | `0 2 * * *` *(Chạy tự động lúc 02:00 AM mỗi ngày)* |
| **Model** | `Gemini 2.5 Pro` hoặc `Gemini 2.5 Flash` |
| **Execution Policy** | `Auto-Proceed` (Tự động thực thi không cần duyệt thủ công) |

---

## 📝 2. Nội Dung Prompt (Copy & Paste vào ô Task Prompt)

```markdown
Bạn là AI Content Creator & Data Automation Agent cho kênh "Lê Lệ Học Tiếng Trung".

### 🎯 NHIỆM VỤ:
Tạo 5 bộ chủ đề từ vựng tiếng Trung (HSK 1, HSK 2 hoặc HSK 3) hoàn toàn mới và thêm vào Google Sheets tab "pinyin" với trạng thái "Pending" để sẵn sàng cho quy trình render video tự động.

---

### 📋 QUY TRÌNH THỰC HIỆN TỪNG BƯỚC:

1. **Kiểm tra dữ liệu hiện có:**
   - Sử dụng môi trường ảo tại `../.venv/bin/python` hoặc `.venv/bin/python`.
   - Kết nối tới Google Sheet (Spreadsheet ID: `1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0`, tab `pinyin`) thông qua `src.gsheet_manager.GSheetManager`.
   - Đọc danh sách tất cả các dòng hiện có để lấy danh sách từ vựng đã dùng (tránh tạo trùng lặp từ vựng quá nhiều).

2. **Tạo 5 chủ đề (Batch) mới:**
   - Mỗi bộ gồm đúng **5 từ vựng** thuộc các cấp độ HSK 1, HSK 2, hoặc HSK 3.
   - Các chủ đề phải gần gũi, hữu ích cho người học (ví dụ: *Đồ ăn thức uống, Cảm xúc & Tính cách, Mua sắm, Du lịch & Giao thông, Trường học & Công việc, Thời tiết & 4 mùa, Gia đình & Xưng hô*...).
   - Định dạng chuẩn cho mỗi ô từ vựng (`Word 1` đến `Word 5`):
     `Chữ Hán | Pinyin đầy đủ có dấu | Pinyin ẩn | Nghĩa tiếng Việt`
     *Ví dụ:* `苹果 | píng guǒ | p _ _ _   g _ _ | Quả táo`
     *(Quy tắc Pinyin ẩn: Giữ lại chữ cái đầu của mỗi âm tiết, các chữ cái còn lại thay bằng dấu gạch dưới `_`)*.

3. **Cập nhật dữ liệu vào Google Sheet:**
   - Cột **#**: Số thứ tự tiếp theo nối tiếp dòng cuối cùng.
   - Cột **Topic**: Tên chủ đề rõ ràng, ví dụ `HSK 1 • Gia Đình & Xưng Hô`.
   - Cột **Level**: Cấp độ tương ứng (`HSK 1`, `HSK 2`, `HSK 3`).
   - Cột **Status**: Đặt chính xác là `Pending`.
   - Cột **Word 1** đến **Word 5**: Chứa thông tin 5 từ vựng đã định dạng.
   - Cột **metadata**: Link Google Drive chứa file metadata (Title + Description cho YT Shorts, TikTok, FB Reels) đã được sinh tự động ngay lúc tạo ý tưởng.
   - Cột **Video**: Để trống `""` (sẽ điền link Google Drive sau khi render video xong).
   - Cột **Youtube**, **Tiktok**, **Facebook**: Để trống `""` (dành cho bước tự động đăng đa kênh).
   - Cột **Created At**: Timestamp thời gian hiện tại (`YYYY-MM-DD HH:MM:SS`).
   - Cột **Notes**: Ghi chú `Tự động sinh bởi Antigravity 2.0 Scheduled Task`.

4. **Thực thi:**
   - Bạn có thể chạy trực tiếp script:
     ```bash
     cd /media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz
     PYTHONPATH=. ../.venv/bin/python scripts/generate_daily_batches.py
     ```
   - Hoặc tự động dùng Python script tương tác với `GSheetManager` để ghi thêm 5 dòng sáng tạo mới.

5. **Xác nhận & Báo cáo:**
   - Kiểm tra lại Google Sheet để đảm bảo 5 dòng mới đã được ghi thành công với trạng thái `Pending`.
   - Xuất ra danh sách 5 chủ đề và các từ vựng vừa tạo để lưu log.
```

---

## 🧭 3. Các Bước Cài Đặt Trên Ứng Dụng Antigravity 2.0

1. Mở ứng dụng **Antigravity 2.0** trên VPS `vpsg16gb`.
2. Ở thanh điều hướng bên trái (Left Sidebar), nhấp vào mục **Scheduled Tasks** (biểu tượng đồng hồ ⏰).
3. Nhấp vào nút **Create New Task** (hoặc dấu `+`).
4. Điền các trường thông tin:
   - **Task Title**: `LeLe - Daily 5 Pinyin Quiz Batches`
   - **Workspace**: Chọn thư mục `/media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz`
   - **Schedule**: Chọn **Cron** và điền `0 2 * * *`
   - **Prompt**: Sao chép toàn bộ nội dung trong ô Markdown ở **Mục 2** và dán vào.
5. Nhấp **Save & Enable**.
