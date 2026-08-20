# 📚 TÀI LIỆU VẬN HÀNH PIPELINE 2.0

Chi tiết toàn bộ quy trình sản xuất, kiểm duyệt và xuất bản tự động của kênh **Lê Lê Học Tiếng Trung (@lelehoctiengtrung)** được trình bày chi tiết tại:

👉 **[PIPELINE_2.0_WORKFLOW.md](file:///media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz/docs/PIPELINE_2.0_WORKFLOW.md)**

### Tóm tắt các thành phần chính:
1. **Kiến trúc 3 tầng Serverless Zero-Secret** (Cloudflare Worker + GitHub Actions + Google Workspace).
2. **Schema 14 Cột Google Sheets Database**.
3. **Lớp kiểm duyệt AI Gatekeeper** với 5 tiêu chí ngôn ngữ khắt khe & quy tắc Strike 3.
4. **Chi tiết 3 GitHub Workflows** (`ScriptNewIdeation.yml`, `Render.yml`, `ProductQC.yml`).
5. **Lịch phát hành tự động Buffer** (3 ca: 07:00, 13:00, 19:00 GMT+7).
6. **Kiểm duyệt trực quan qua Telegram Bot**.
