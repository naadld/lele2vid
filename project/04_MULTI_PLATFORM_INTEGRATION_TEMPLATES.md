# 🔌 CẨM NANG LIÊN KẾT 6 NỀN TẢNG ĐÁM MÂY (INTEGRATION PLAYBOOK)
## Hướng dẫn kết nối Cloudflare, GitHub Actions, Google Sheets, Google Drive, Buffer & Telegram

---

## 1. LIÊN KẾT GOOGLE SHEETS (SHEETS API V4 QUA RS256 JWT)
* Không cần cài thư viện ngoài trên Cloudflare Worker.
* Sử dụng WebCrypto nguyên bản (`crypto.subtle.importKey`) để ký JWT token RS256 và lấy Access Token trực tiếp từ Google OAuth2 Endpoint (`https://oauth2.googleapis.com/token`).
* Đọc/Ghi dữ liệu qua REST API chuẩn (`https://sheets.googleapis.com/v4/spreadsheets/...`).

---

## 2. LIÊN KẾT GITHUB ACTIONS (DISPATCH WORKFLOWS TỪ CLOUDFLARE)
Khi người dùng bấm nút `[🎬 Render Video]` hoặc gõ `/render` trên Telegram:
* Cloudflare Worker gửi HTTP POST request đến GitHub API:
  ```http
  POST https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_file}/dispatches
  Authorization: Bearer {GITHUB_TOKEN}
  Content-Type: application/json
  
  {
    "ref": "main",
    "inputs": { "row_id": "16", "quality": "qh" }
  }
  ```

---

## 3. LIÊN KẾT BUFFER GRAPHQL API (XUẤT BẢN ĐA KÊNH ĐỒNG LOẠT)
* Buffer GraphQL Endpoint: `https://api.buffer.com`
* **Cơ chế "Share Now" (Đăng Ngay):** Thay vì đẩy vào hàng đợi Buffer (dễ bị delay hoặc kẹt), gọi trực tiếp mutation `createPost` với tham số `mode: NOW`:
  ```graphql
  mutation CreatePost($input: CreatePostInput!) {
    createPost(input: $input) {
      post {
        id
        status
      }
    }
  }
  ```
* **Tối ưu link video Google Drive:** Chuyển link xem của Drive sang link streaming trực tiếp `https://drive.usercontent.google.com/download?id={fileId}&export=download&authuser=0` để Buffer tải video với tốc độ cao nhất (HTTP 200 `video/mp4`).

---

## 4. LIÊN KẾT TELEGRAM BOT (WEBHOOK & HUMAN-IN-THE-LOOP)
* Đăng ký Webhook 1 lần duy nhất:
  ```bash
  curl "https://api.telegram.org/bot{TOKEN}/setWebhook?url=https://{WORKER_URL}/webhook"
  ```
* Mọi tương tác (Gõ lệnh `/status`, `/ideate`, `/render`, `/publish`, `/fix` hoặc bấm nút Callback `approve:16`, `reset:16`, `delete:16`) đều được Cloudflare Worker xử lý dưới 50ms và cập nhật giao diện tin nhắn tức thì.

---

## 5. QUY CHUẨN AN TOÀN BẢO MẬT (ZERO-SECRET MATRIX)

| Nền Tảng | Nơi Lưu Trữ Secret | Lệnh / Thao Tác Cài Đặt |
| :--- | :--- | :--- |
| **Cloudflare Worker** | Encrypted Worker Secrets | `wrangler secret put TELEGRAM_BOT_TOKEN`<br>`wrangler secret put BUFFER_ACCESS_TOKEN`<br>`wrangler secret put GITHUB_TOKEN`<br>`wrangler secret put GEMINI_API_KEYS` |
| **GitHub Actions** | Repository Encrypted Secrets | `Settings ➔ Secrets and variables ➔ Actions`<br>Thêm `GCP_SERVICE_ACCOUNT_JSON`, `GDRIVE_REFRESH_TOKEN` |
| **Git Repository** | `.gitignore` | Chặn tuyệt đối mọi file `.env`, `.json`, `.key`, `.token` |
