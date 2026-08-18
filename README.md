# 🇨🇳 Kênh Tự Động: Lê Lê Học Tiếng Trung (PinyinQuiz)

> **Hệ thống đã chuyển đổi 100% sang Cloud Serverless (Cloudflare Worker + GitHub Actions).**  
> Không phụ thuộc vào VPS hoặc máy tính cá nhân. Tự động sản xuất, kiểm duyệt và đăng bài 24/7.

---

## 🔗 Các Liên Kết Dự Án Quan Trọng:

- **📦 Google Drive Backup:** [Thư mục Backup GDrive](https://drive.google.com/drive/u/0/folders/1k1Xamrrl1CXOFqXo2QhxSyrnesyQQr8N)
  - File ZIP nén đầy đủ: [`lele_pinyinquiz_full_backup.zip`](https://drive.google.com/file/d/1Q7xkkZ4lei_DS3n0ywmKAAw0sLRz6lrO/view?usp=drivesdk)
- **🚀 GitHub Repository:** [`https://github.com/naadld/lele2vid`](https://github.com/naadld/lele2vid)
- **⚡ Cloudflare Worker Live:** [`https://lele-pinyinquiz.hothihuong113.workers.dev`](https://lele-pinyinquiz.hothihuong113.workers.dev)
- **🤖 Telegram Control Bot:** [@lelepinyinBot](https://t.me/lelepinyinBot)
- **📊 Google Sheets Dữ Liệu:** [Tab `pinyin`](https://docs.google.com/spreadsheets/d/1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0/edit)

---

## ⏰ Lịch Vận Hành Hằng Ngày (Tự Động 100%):
1. **01:00 Sáng VN (UTC 18:00):** Tự động sinh ý tưởng từ vựng HSK ➔ Kích hoạt GitHub Action render video ➔ Bắn video sang Telegram kèm 4 nút duyệt (`Approve` / `Reset` / `Delete` / `Cancel`).
2. **07:00 Sáng VN (UTC 00:00):** Retry lỗi `Error` ➔ Tự động đăng 1 video `Ready` lên 3 nền tảng (TikTok, Reels, Shorts) qua Buffer GraphQL API.
3. **13:00 Chiều VN (UTC 06:00):** Retry lỗi `Error` ➔ Tự động đăng 1 video `Ready` tiếp theo lên 3 nền tảng qua Buffer GraphQL API.

---

## 🛠️ Khi Cần Khôi Phục / Chỉnh Sửa Mã Nguồn Trên Máy Mới:

```bash
# Cách 1: Clone trực tiếp từ GitHub
git clone https://github.com/naadld/lele2vid.git

# Cách 2: Tải file zip từ Google Drive và giải nén
unzip lele_pinyinquiz_full_backup.zip
```
