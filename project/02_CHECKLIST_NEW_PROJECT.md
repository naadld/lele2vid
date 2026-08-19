# ✅ CHECKLIST 20 BƯỚC KHỞI CHẠY DỰ ÁN MỚI (GO-LIVE CHECKLIST)
## Áp dụng khi nhân bản sang Kênh mới (Tiếng Anh, Tiếng Pháp, v.v.)

---

### GIAI ĐOẠN 1: THIẾT LẬP DỮ LIỆU & NỀN TẢNG (SETUP)
- [ ] **1. Google Sheet:** Tạo Sheet mới, tạo Tab nội dung với đủ 16 cột (A ➔ P).
- [ ] **2. Google Cloud Service Account:** Cấp quyền `Editor` cho email Service Account vào Google Sheet & thư mục Google Drive.
- [ ] **3. Buffer Channels:** Kết nối đủ 3 kênh (YouTube Channel, TikTok Account, Facebook Page) vào Buffer Dashboard.
- [ ] **4. Telegram Bot:** Tạo bot mới qua `@BotFather`, lấy Bot Token và Chat ID cá nhân (`1187577977`).

---

### GIAI ĐOẠN 2: THIẾT KẾ ĐỒ HỌA & NỘI DUNG (CREATIVE)
- [ ] **5. Giọng đọc TTS:** Chọn đúng giọng đọc của ngôn ngữ mục tiêu trong `edge-tts` (ví dụ: `en-US-JennyNeural`, `fr-FR-DeniseNeural`).
- [ ] **6. Template Manim:** Thiết kế layout 3 tầng (Từ vựng ➔ Phiên âm IPA ➔ Nghĩa tiếng Việt).
- [ ] **7. Khung hình Bìa 0.75s:** Đảm bảo bố cục tiêu đề to rõ, màu vàng Gold 3D tại giây `00:00:00`.
- [ ] **8. AI System Prompt:** Cấu hình quy tắc sư phạm, chống trùng lặp từ vựng và ép trả về JSON chuẩn.

---

### GIAI ĐOẠN 3: LÁ CHẮN KIỂM ĐỊNH & BẢO VỆ CHẤT LƯỢNG (GATEKEEPER)
- [ ] **9. Pre-Render Gatekeeper:** Cấu hình luật chặn nghĩa dài (> 30 ký tự), sai chính tả.
- [ ] **10. Auto-QC Gatekeeper:** Cấu hình kiểm tra file video MP4, độ tương phản khung hình 00:00.
- [ ] **11. AI Auto-Healing:** Cấu hình lệnh `/fix` để tự động sửa các bài bị `Failed` sang `Pending`.

---

### GIAI ĐOẠN 4: DEPLOY SERVERLESS & HẸN GIỜ (DEPLOYMENT)
- [ ] **12. Cloudflare Worker:** Cấu hình `wrangler.toml` (Biến môi trường, Tab Sheet, Chat ID).
- [ ] **13. Cloudflare Encrypted Secrets:** Nạp `TELEGRAM_BOT_TOKEN`, `BUFFER_ACCESS_TOKEN`, `GEMINI_API_KEYS`.
- [ ] **14. Webhook Telegram:** Đăng ký Webhook trỏ về Cloudflare Worker (`/webhook`).
- [ ] **15. GitHub Actions Secrets:** Nạp `GCP_SERVICE_ACCOUNT_JSON`, `GDRIVE_REFRESH_TOKEN`, `TELEGRAM_BOT_TOKEN`.
- [ ] **16. Cron Schedules:** Kiểm tra múi giờ 5 mốc quan trọng (01:00 Sáng, 06:30 QC, 07:00 Đăng, 12:01 Dashboard, 12:30 QC, 13:00 Đăng, 18:01 Dashboard).

---

### GIAI ĐOẠN 5: KIỂM THỬ THỰC TẾ (TESTING & VERIFICATION)
- [ ] **17. Test Sinh Ý Tưởng:** Gõ `/ideate` trên Telegram, kiểm tra xem dòng mới có xuất hiện trên Google Sheet với trạng thái `Pending` không.
- [ ] **18. Test Render Video:** Bấm nút `[Render Ngay]`, kiểm tra video `.mp4` có được gửi về Telegram và có ảnh bìa 0.75s không.
- [ ] **19. Test Auto-QC:** Chạy `/qc` kiểm tra xem video có tự động chuyển từ `Video` sang `Ready` không.
- [ ] **20. Test Đăng Thử Nghiệm:** Gõ `/publish` kiểm tra xem video có xuất hiện trên YouTube, TikTok, Facebook Reels không.
