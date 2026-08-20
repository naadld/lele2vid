# 📐 TÀI LIỆU BÀN GIAO KỸ THUẬT PIPELINE 2.0 (HANDOFF)
## HỆ THỐNG TỰ ĐỘNG HÓA SẢN XUẤT VIDEO DẠNG NGẮN TOÁN HỌC LỚP 4 - 5 - 6
### (Kiến Trúc Zero-Secret & Multi-Tier AI Gatekeeper)

---

## 1. TỔNG QUAN KIẾN TRÚC HỆ THỐNG (PIPELINE 2.0)

Hệ thống được thiết kế theo mô hình **Serverless Hoàn Toàn (100% Zero-Maintenance)**, kết hợp giữa **Cloudflare Workers (Bộ Não Điều Phối & Giám Sát)** và **GitHub Actions (Cỗ Máy Tính Toán Nặng & Render Manim)**:

```mermaid
flowchart TD
    subgraph MasterPlane ["☁️ CLOUDFLARE WORKER (MASTER ORCHESTRATOR)"]
        CronTimer["⏰ Cron Trigger 00:01 GMT+7 (17:01 UTC)"]
        CF_GK["🛡️ Gatekeeper 1 (Agnes AI / Workers AI Fallback)\n• Kiểm tra tính sư phạm & đáp án Toán 4-5-6\n• Strike 3: Xóa vĩnh viễn dòng lỗi sau 3 lần"]
        CF_Publish["🚀 Buffer Cron (07:00 • 13:00 • 19:00)\n• Đăng tự động lên YouTube Shorts, TikTok, FB Reels"]
        TG_Bot["🤖 Telegram Bot (@BotFather)\n• Báo cáo trạng thái, cảnh báo lỗi, nút kiểm duyệt"]
    end

    subgraph GitHubEngine ["⚙️ GITHUB ACTIONS (COMPUTE ENGINE - ZERO SECRET)"]
        WF1["1️⃣ ScriptNewIdeation.yml\n• Nhận Ephemeral Gemini Keys qua TLS\n• Đọc Negative Context từ GSheet\n• Sinh 5 bài toán/ngày (Lớp 4 - 5 - 6)\n• Giãn cách 60s & Xoay vòng 6 Keys\n• Webhook POST về Cloudflare"]
        WF2["2️⃣ Render.yml\n• Render Manim MP4 1080x1920 60fps\n• Giữ khung Bìa 0.75s tại 00:00:00\n• Đọc đề TTS tiếng Việt chuẩn\n• Tải video lên GDrive ➔ Set 'Video'"]
        WF3["3️⃣ ProductQC.yml\n• OpenCV & FFprobe kiểm tra độ nét, âm thanh, khung bìa\n• Đạt chuẩn 100% ➔ Set 'Ready'"]
    end

    subgraph DataStorage ["📊 STORAGE & GOOGLE WORKSPACE"]
        GS["📋 Google Sheet (Tab: 'toan' hoặc 'math')\n• Quản lý trạng thái: Pending ➔ Video ➔ Ready ➔ Published"]
        GD["📁 Google Drive (Folder Video Toán 4-5-6)"]
    end

    CronTimer -->|Dispatch kèm Dynamic Ephemeral Keys| WF1
    WF1 -->|POST /api/receive-ideas| CF_GK
    CF_GK -- "❌ Vi phạm (Lần 1-2)" -->|Gọi Step 2 Re-gen riêng dòng lỗi| WF1
    CF_GK -- "❌ Vi phạm lần 3" -->|DELETE cả dòng cũ khỏi Sheet| GS
    CF_GK -- "✅ Đạt chuẩn 100%" -->|Ghi Sheet & Set 'Pending'| GS

    GS -->|Kích hoạt khi có dòng Pending| WF2
    WF2 -->|Upload video MP4| GD
    WF2 -->|Ghi link video & Set 'Video'| GS
    WF2 -->|Kích hoạt Post-QC| WF3
    WF3 -->|Đạt chuẩn 100% ➔ Set 'Ready'| GS

    CF_Publish -->|Lấy 1 video 'Ready' trên cùng| GS
    CF_Publish -->|Đăng video qua Buffer API| DataStorage
```

---

## 2. CẤU TRÚC BẢNG TÍNH GOOGLE SHEETS (SHEET SCHEMA)

Bảng tính Google Sheets được cấu trúc theo 14 cột tiêu chuẩn:

| Cột | Tên Cột | Mô tả & Định dạng cho Kênh Toán 4-5-6 |
| :--- | :--- | :--- |
| **A** | `ID` | Mã định danh duy nhất của video (Ví dụ: `1`, `2`, `3`...). |
| **B** | `Topic` | Tên dạng toán hoặc chủ đề (Ví dụ: `Toán Lớp 4 • Phép Chia Phân Số`, `Toán Lớp 5 • Tính Vận Tốc`). |
| **C** | `Level` | Trình độ / Lớp: `Lớp 4`, `Lớp 5`, `Lớp 6` (Luân phiên đều đặn). |
| **D** | `Status` | Trạng thái vòng đời: `Pending` ➔ `Video` ➔ `Ready` ➔ `Published` (hoặc `Error`). |
| **E** | `Word_1` | Bài toán 1: `Đề bài | Gợi ý / Công thức | Đáp án ẩn | Lời giải chi tiết`. |
| **F** | `Word_2` | Bài toán 2: Định dạng tương tự bài 1. |
| **G** | `Word_3` | Bài toán 3: Định dạng tương tự bài 1. |
| **H** | `Word_4` | Bài toán 4: Định dạng tương tự bài 1. |
| **I** | `Word_5` | Bài toán 5: Định dạng tương tự bài 1. |
| **J** | `Metadata` | Tiêu đề YouTube Shorts, Caption TikTok/Reels, Hashtags SEO. |
| **K** | `Video` | Đường link xem video trực tiếp trên Google Drive. |
| **L** | `YouTube` | Trạng thái đăng bài YouTube Shorts (`Published` hoặc `Error`). |
| **M** | `TikTok` | Trạng thái đăng bài TikTok (`Published` hoặc `Error`). |
| **N** | `Facebook` | Trạng thái đăng bài Facebook Reels (`Published` hoặc `Error`). |

---

## 3. NGUYÊN TẮC BẢO MẬT ZERO-SECRET TRÊN GITHUB

1. **Tuyệt đối không lưu API Key tĩnh trên GitHub:** Toàn bộ API Keys (Google AI Studio, Agnes AI, Token Buffer, Service Account...) được cất giữ mã hóa 100% trên Cloudflare Secrets (`wrangler secret put`).
2. **Cơ chế Bơm Khóa Động (Dynamic Ephemeral Injection):** Khi Cloudflare Worker kích hoạt GitHub Actions (`workflow_dispatch`), nó sẽ truyền API Keys vào payload HTTPS TLS 1.3. GitHub Action Runner nhận vào RAM, thực thi và tự động xóa sổ khi đóng container.
3. **Mặt nạ bảo mật trên Console Log:** Tất cả lệnh thực thi đều tự động che giấu Key (dạng `AIzaSy...****`).

---

## 4. QUY TRÌNH 3 WORKFLOWS GITHUB ACTIONS

### 📁 1. Workflow `ScriptNewIdeation.yml` (Sáng Tạo Bài Toán)
* **Step 1 (Batch Ideation):**
  - Chạy lúc `00:01 GMT+7` (17:01 UTC) do Cloudflare Worker dispatch.
  - Tự động sinh **5 bài toán mới / ngày** với độ đa dạng xoay vòng: `Lớp 4 ➔ Lớp 5 ➔ Lớp 6 ➔ Lớp 4...`.
  - Quét 100 dòng gần nhất từ Google Sheet để nạp Negative Context chống trùng lặp dạng toán hoặc số liệu.
  - Giãn cách **60 giây** giữa các bài toán và **xoay vòng lần lượt 6 Google AI Studio Keys** (Gemini 3.7 Flash).
  - Bắn Webhook `POST /api/receive-ideas` sang Cloudflare Gatekeeper 1.
* **Step 2 (Targeted Single-Row Re-generation):**
  - Khi Gatekeeper 1 từ chối 1 dòng, Cloudflare tự động gọi Step 2 để viết lại riêng dòng đó mà không làm ảnh hưởng các dòng khác.

### 📁 2. Workflow `Render.yml` (Sản Xuất Video Manim 60fps)
* Quét toàn bộ dòng có trạng thái `Pending`.
* Chạy công cụ Manim sinh video toán học chuyển động 1080x1920 (9:16) 60fps:
  - **Khung Bìa (High-CTR Cover):** Giữ tĩnh 0.75 giây đầu video tại mốc `00:00:00`.
  - **Âm thanh TTS:** Sử dụng giọng đọc tiếng Việt tự nhiên (`vi-VN-HoaiMyNeural` hoặc `vi-VN-NamMinhNeural`).
* Tải video lên thư mục Google Drive chuyên dụng và cập nhật trạng thái dòng thành `Video`.
* Tự động kích hoạt `ProductQC.yml`.

### 📁 3. Workflow `ProductQC.yml` (Auto-QC Hậu Kỳ Vật Lý)
* Sử dụng thư viện **OpenCV & FFprobe** để rà soát chất lượng video:
  - Đảm bảo độ nét, độ sáng khung hình 00:00:00.
  - Đảm bảo stream âm thanh không bị câm (muted).
  - Đảm bảo thời lượng video đạt chuẩn short-form (15s – 120s).
* Khi vượt qua 100%, tự động chuyển trạng thái dòng thành `Ready`.

---

## 5. QUY TẮC GATEKEEPER 1 (TIÊU CHÍ TOÁN HỌC LỚP 4-5-6)

Gatekeeper 1 chạy độc lập trên Cloudflare Worker (sử dụng Agnes AI / Cloudflare Workers AI fallback) để kiểm định:
1. **Tính chính xác toán học 100%:** Đề bài, phép tính và đáp án phải hoàn toàn chính xác, không có lỗi suy luận logic.
2. **Chuẩn chương trình SGK Lớp 4 - 5 - 6:** Không dùng kiến thức vượt cấp, câu từ trong sáng, dễ hiểu.
3. **100% Tiếng Việt Chuẩn:** Không dùng từ ngữ lai căng, không lẫn tiếng Anh.
4. **Cấu trúc dữ liệu chuẩn:** Đủ 5 bài toán con trong 1 video, định dạng phân cách rõ ràng.
5. **Chống trùng lặp tuyệt đối:** Không lặp lại cùng một đề bài hoặc cặp số liệu với các video trước đó trong lịch sử Sheet.
6. **Cơ chế Strike 3:** Cho phép tạo lại tối đa 2 lần (Step 2). Nếu đến lần thứ 3 vẫn không đạt chuẩn ➔ **Xóa vĩnh viễn dòng cũ khỏi Google Sheet**.

---

## 6. LỊCH PHÁT HÀNH TỰ ĐỘNG (3 CA / NGÀY)

* **07:00 Sáng (00:00 UTC):** Lấy video `Ready` đầu tiên trên cùng ➔ Đăng bài qua Buffer API.
* **13:00 Chiều (06:00 UTC):** Lấy video `Ready` tiếp theo ➔ Đăng bài qua Buffer API.
* **19:00 Tối (12:00 UTC):** Lấy video `Ready` tiếp theo ➔ Đăng bài qua Buffer API.
* **Tự động Retry:** Nếu có kênh mạng xã hội nào bị lỗi (Status: `Error`), hệ thống tự động thử lại tối đa 2 lần trước khi chuyển sang video mới.

---

## 7. BƯỚC TRIỂN KHAI CHO KÊNH MỚI (TOÁN LỚP 4-5-6)

1. Điền toàn bộ thông số vào file [`CONFIG_PARAMETERS_TEMPLATE.txt`](file:///media/vpsg16gb/HaRiDisk/CHANNELS/lelehoctiengtrung/CONFIG_PARAMETERS_TEMPLATE.txt).
2. Tạo Google Sheet mới với 14 cột theo schema mục 2 và cấp quyền `Editor` cho email Service Account.
3. Cấu hình secrets trên Cloudflare Worker qua lệnh: `npx wrangler secret put <TÊN_SECRET>`.
4. Deploy Worker bằng lệnh: `npx wrangler deploy`.
5. Đẩy code và workflows lên GitHub Repository mới.
