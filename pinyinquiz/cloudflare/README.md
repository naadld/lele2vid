# 🚀 Lê Lê Học Tiếng Trung - Cloudflare AI Worker & Serverless Pipeline

Hệ thống tự động hóa toàn diện **100% Độc lập với VPS**, sử dụng nền tảng **Cloudflare Workers AI**, **Cloudflare Cron Triggers**, **Google Sheets API v4**, **GitHub Actions** và **Buffer API**.

---

## 🌟 Tính Năng Chính

1. **Telegram Bot Command Webhook:**
   - Điều khiển mọi hoạt động ngay trên Telegram chat:
     - `/ideate` hoặc `/generate`: Kích hoạt AI sinh 5 bộ chủ đề từ vựng HSK mới + đẩy vào Google Sheet + tự động trigger GitHub Action render video.
     - `/publish`: Đăng ngay 1 video trạng thái **Ready** lên Buffer (TikTok, Facebook Reels, YouTube Shorts).
     - `/render`: Kích hoạt thủ công GitHub Action để render video Pending.
     - `/status`: Báo cáo thống kê số lượng video (Pending, Ready, Published...).
     - `/help`: Xem hướng dẫn lệnh.

2. **Cloudflare Workers AI (`@cf/meta/llama-3.3-70b-instruct`):**
   - Sinh từ vựng HSK 1 - HSK 3 chuẩn xác với chữ Hán, Pinyin đầy đủ thanh điệu và nghĩa tiếng Việt.
   - Tự động sinh `Hidden Pinyin` chuẩn quy tắc (`p _ _ _   g _ _`).
   - Tự động sinh Metadata viral (Tiêu đề, Caption, Hashtags) tối ưu cho từng mạng xã hội.
   - Tích hợp sẵn Từ điển dự phòng (Fallback Vocab Bank) khi AI bận.

3. **Lịch Đăng Bài Tự Động 2 Lần Mỗi Ngày (Cloudflare Cron Triggers):**
   - **07:00 Sáng** (UTC 00:00)
   - **13:00 Chiều** (UTC 06:00)
   - Tự động lấy 1 video trạng thái `Ready`, đính kèm metadata và đăng lên cả 3 kênh qua **Buffer API**.
   - Cập nhật trạng thái trên Google Sheet thành `Published` và báo cáo qua Telegram.

4. **100% Không Cần VPS:**
   - Render video nặng được chạy trên **GitHub Actions Cloud Runner**.
   - Điều phối và đăng bài chạy trên **Cloudflare Serverless Edge Network**.

---

## 📂 Cấu Trúc Thư Mục

```text
pinyinquiz/cloudflare/
├── wrangler.toml              # Cấu hình Cloudflare Worker, AI binding, Cron Triggers
├── package.json               # Package config
├── .env.example               # Mẫu danh sách Secret và Env vars
├── README.md                  # Hướng dẫn chi tiết này
└── src/
    ├── index.js               # Entrypoint (Router HTTP, Webhook, Cron Scheduled)
    ├── config.js              # Quản lý cấu hình & biến môi trường
    ├── ai_ideation.js         # Cloudflare Workers AI + Fallback Vocab Bank
    ├── pinyin_helper.js       # Xử lý Pinyin & tạo Hidden Pinyin
    ├── metadata_helper.js     # Sinh Tiêu đề & Caption cho YouTube / TikTok / FB Reels
    ├── google_sheets.js       # Google Sheets API v4 (Pure WebCrypto JWT RS256)
    ├── github_trigger.js      # Kích hoạt GitHub Action workflow_dispatch
    ├── buffer_publisher.js    # Buffer API v1 client (Đăng video đa kênh)
    └── telegram.js            # Telegram Bot client & format thông báo HTML
```

---

## 🛠️ Hướng Dẫn Cài Đặt & Triển Khai

### Bước 1: Cài đặt Wrangler CLI (nếu chưa có)

```bash
npm install -g wrangler
# Đăng nhập tài khoản Cloudflare
wrangler login
```

---

### Bước 2: Cấu Hình Các Secrets Trên Cloudflare Worker

Chuyển vào thư mục `cloudflare`:
```bash
cd /media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/pinyinquiz/cloudflare
```

Chạy các lệnh sau để nạp thông tin bảo mật vào Cloudflare:

#### 1. Google Service Account (Đọc/Ghi Google Sheets)
Lấy từ file `service_account.json` của bạn:
```bash
wrangler secret put GCP_SERVICE_ACCOUNT_EMAIL
# Nhập email: your-service-account@...iam.gserviceaccount.com

wrangler secret put GCP_SERVICE_ACCOUNT_PRIVATE_KEY
# Nhập toàn bộ chuỗi private_key bao gồm cả:
# -----BEGIN PRIVATE KEY-----
# ...
# -----END PRIVATE KEY-----
```

#### 2. Telegram Bot
```bash
wrangler secret put TELEGRAM_BOT_TOKEN
# Nhập Bot Token từ @BotFather (ví dụ: 123456789:ABCdefGhIJK...)

wrangler secret put TELEGRAM_CHAT_ID
# Nhập Chat ID của bạn nhận thông báo (ví dụ: 123456789)

wrangler secret put TELEGRAM_WEBHOOK_SECRET
# Nhập một chuỗi bí mật bất kỳ (ví dụ: lele_secret_token_2026)
```

#### 3. GitHub Token (Kích hoạt workflow render)
Tạo Personal Access Token (Classic hoặc Fine-grained) trên GitHub với quyền `repo` hoặc `actions:write`:
```bash
wrangler secret put GITHUB_TOKEN
# Nhập: ghp_xxxxxxxxxxxxxxxxxxxx
```

#### 4. Buffer API Token & Profile IDs
Lấy Access Token tại: [Buffer Developer Portal](https://buffer.com/developers/api)
```bash
wrangler secret put BUFFER_ACCESS_TOKEN
# Nhập: 1/xxxxxxxxxxxxxxxxxxxxxxxx

wrangler secret put BUFFER_PROFILE_IDS
# Nhập danh sách Profile IDs phân tách bằng dấu phẩy (TikTok, Facebook Reels, YouTube)
# Ví dụ: 64f1234567890abcdef12345,64f1234567890abcdef12346,64f1234567890abcdef12347
```
*(Nếu chưa biết Profile IDs, bạn có thể gọi endpoint: `https://api.bufferapp.com/1/profiles.json?access_token=YOUR_TOKEN` để lấy danh sách id).*

---

### Bước 3: Deploy Lên Cloudflare Worker

```bash
wrangler deploy
```
Sau khi deploy thành công, bạn sẽ nhận được một URL của Worker, ví dụ:
`https://lele-pinyin-worker.<your-subdomain>.workers.dev`

---

### Bước 4: Thiết Lập Webhook Cho Telegram Bot

Chạy lệnh curl sau để trỏ Webhook từ Telegram về Cloudflare Worker:

```bash
curl -F "url=https://lele-pinyin-worker.<your-subdomain>.workers.dev/webhook" \
     -F "secret_token=YOUR_TELEGRAM_WEBHOOK_SECRET" \
     https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook
```

Sau khi thiết lập xong, mở Telegram và gõ lệnh `/start` hoặc `/help` tới Bot để kiểm tra!

---

## 🎯 Luồng Hoạt Động Hoàn Chỉnh

```text
1. Người dùng gõ /ideate trên Telegram Bot (hoặc Cron tự động).
2. Cloudflare Worker AI (@cf/meta/llama-3.3-70b) sinh 5 bộ từ vựng HSK.
3. Worker ghi 5 hàng vào Google Sheet tab 'pinyin' với trạng thái 'Pending'.
4. Worker tự động gọi GitHub API kích hoạt 'daily_render.yml'.
5. GitHub Actions Runner:
   - Tải tài nguyên & render video chất lượng cao bằng Manim.
   - Upload video lên Google Drive.
   - Cập nhật trạng thái trên Google Sheet thành 'Ready'.
6. Hàng ngày lúc 07:00 Sáng và 13:00 Chiều:
   - Cloudflare Cron Trigger tự động quét video có trạng thái 'Ready'.
   - Gọi Buffer API để đăng video lên TikTok, Facebook Reels và YouTube Shorts.
   - Đổi trạng thái trên Google Sheet thành 'Published'.
   - Gửi thông báo thành công về Telegram!
```
