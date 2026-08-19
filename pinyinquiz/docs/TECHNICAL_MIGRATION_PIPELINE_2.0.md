# 📘 TÀI LIỆU KỸ THUẬT CHUYỂN ĐỔI HỆ THỐNG PIPELINE 2.0 (TECHNICAL MIGRATION SPECIFICATION)
## HỆ THỐNG TỰ ĐỘNG HÓA SẢN XUẤT VIDEO ĐA NỀN TẢNG (ZERO-SECRET & MULTI-TIER AI GATEKEEPER)
**Kênh:** *Lê Lê Học Tiếng Trung* (`@lelehoctiengtrung`)  
**Phiên bản:** `Pipeline 2.0 - High-Security & Deterministic AI Architecture`

---

## 1. TỔNG QUAN KIẾN TRÚC PIPELINE 2.0 (SYSTEM BLUEPRINT)

Pipeline 2.0 phân tách triệt để 2 vai trò:
1. **Creator (Cỗ máy sáng tạo & Render - GitHub Actions tại Mỹ):** Sử dụng 6 Keys **Google AI Studio (Gemini 3.7 Flash)** với IP Mỹ để viết kịch bản, render Manim 1080x1920 và Auto-QC.
2. **Auditor & Master Orchestrator (Giám khảo kiểm duyệt độc lập & Điều phối - Cloudflare Worker):** Sử dụng **Agnes AI** và **Cloudflare Workers AI** làm Giám khảo Gatekeeper 1 nghiêm ngặt, chấm điểm độc lập kịch bản, quản lý Google Sheet, điều phối vòng lặp Self-Healing và phân phối Buffer 3 ca/ngày.

```mermaid
flowchart TD
    subgraph ControlPlane ["1. CONTROL PLANE & AUDITOR (Cloudflare Worker)"]
        Cron["⏰ Cron Thứ 7 (00:01 GMT+7)\nhoặc /ideate Telegram"]
        CF_GK["🧐 Gatekeeper 1 (Agnes AI / Workers AI)\n• Chấm điểm 100% Giản thể, Pinyin, Nghĩa TV\n• Retry tối đa 2 lần\n• Lần 3: DELETE cả dòng cũ"]
        GS["📊 Google Sheets Database\n(Tab: 'pinyin')"]
        BF["🚀 Buffer API Publisher\n(07:00, 13:00, 19:00)"]
    end

    subgraph ComputePlane ["2. SECURE COMPUTE PLANE (GitHub Actions - US Runners)"]
        WF1["📝 Workflow 1: ScriptNewIdeation.yml\n• Step 1: Batch 30 ideas (Delay 60s, Rotate 6 Keys)\n• Step 2: Single-Row Re-generation"]
        WF2["🎬 Workflow 2: Render.yml\n• Manim 1080x1920 + Bìa 0.75s tại 00:00\n• Upload Google Drive ➔ Set 'Video'"]
        WF3["🛡️ Workflow 3: ProductQC.yml\n• OpenCV Post-Render Inspector\n• Quét độ sáng bìa, thời lượng ➔ Set 'Ready'"]
    end

    Cron -->|1. Dispatch Workflow kèm Ephemeral Payload| WF1
    WF1 -->|2. Webhook POST Kịch Bản Mới| CF_GK
    CF_GK -- "❌ Vi phạm (Lần 1-2)" -->|Gọi Step 2 Re-gen riêng dòng lỗi| WF1
    CF_GK -- "❌ Vi phạm lần 3" -->|DELETE cả dòng cũ khỏi Sheet| GS
    CF_GK -- "✅ Đạt chuẩn 100%" -->|Ghi Sheet & Set 'Pending'| GS
    
    GS -->|Kích hoạt khi đủ 30 dòng Pending| WF2
    WF2 -->|Tải video lên GDrive & Set 'Video'| GS
    WF2 -->|Kích hoạt Post-QC| WF3
    WF3 -->|Đạt chuẩn 100% ➔ Set 'Ready'| GS
    
    GS -->|Lấy 1 video Ready trên cùng| BF
```

---

## 2. CHẾ ĐỘ BẢO MẬT TUYỆT MẬT (ZERO-SECRET ARCHITECTURE TRÊN GITHUB)

Để đảm bảo **không lưu trữ bất kỳ API Key / Token tĩnh nào trên GitHub Repository**:

```text
[Cloudflare Worker] --(1. Mã hóa Payload + Dynamic Ephemeral Key)--> [GitHub Actions Dispatch Inputs]
                                                                             ⬇️
[GitHub Actions Runner] <--(2. Chỉ giữ trong bộ nhớ RAM phiên chạy, hủy ngay khi xong)
```

1. **Không lưu cứng Google AI Studio Keys trên GitHub:** Toàn bộ 6 Keys Google AI Studio được lưu trữ an toàn dưới dạng Cloudflare Encrypted Secrets (`wrangler secret put GEMINI_API_KEYS`).
2. **Cơ chế Dynamic Ephemeral Dispatch:** Khi Cloudflare kích hoạt GitHub Actions (`workflow_dispatch`), Worker sẽ truyền API Key tương ứng vào trường `inputs` của request được bảo vệ bởi HTTPS TLS 1.3.
3. **Bộ nhớ RAM tạm thời:** GitHub Action Runner nhận Key qua biến môi trường phiên chạy (Environment Variable ephemeral), sử dụng xong sẽ tự động hủy toàn bộ RAM khi container đóng.
4. **Không lưu log:** Mọi câu lệnh gọi API trong Python script đều được che giấu (masking `AQ.Ab8...****`) trên console log của GitHub Actions.

---

## 3. THIẾT KẾ CHI TIẾT 3 GITHUB ACTIONS WORKFLOWS

### 📁 Workflow 1: `ScriptNewIdeation.yml` (Sáng Tạo Kịch Bản)
Workflow này được chia làm **2 Steps chuyên biệt**:

#### 🔹 Step 1: Sinh 30 Ideas Mới Hàng Tuần (Batch Ideation)
* **Thời điểm kích hoạt:** `00:01 Sáng Thứ 7 (GMT+7)` (tương ứng `17:01 Thứ 6 UTC`) qua Cloudflare Cron hoặc lệnh `/ideate 30`.
* **Quy trình tuần tự (Sequential Pipeline):**
  1. Đọc toàn bộ lịch sử 100 dòng gần nhất từ Google Sheet để nạp danh sách từ vựng và chủ đề đã dùng vào ngữ cảnh loại trừ (Negative Context).
  2. Chạy lần lượt từng dòng một: **Hoàn thành dòng $N$ ➔ Đợi 60 giây ➔ Chạy dòng $N+1$**.
  3. **Cơ chế Xoay Vòng 6 Keys (60s Delay Key-Rotation):**
     $$\text{Key Index} = (N \pmod 6) + 1$$
     Mỗi dòng sử dụng 1 API Key Gemini 3.7 Flash khác nhau và giãn cách đúng **60 giây**. Đảm bảo **100% không bao giờ chạm trần Rate Limit (15 RPM)** của Google AI Studio.
  4. Sau khi sinh xong mỗi dòng, gửi ngay kết quả về Webhook của Cloudflare để Gatekeeper 1 kiểm định.

#### 🔹 Step 2: Tái Sinh Dòng Bị Lỗi (Targeted Row Re-Generation)
* **Thời điểm kích hoạt:** Khi Cloudflare Gatekeeper phát hiện 1 dòng cụ thể không đạt chuẩn.
* **Cơ chế hoạt động:**
  - Nhận tham số đầu vào: `row_id`, `rejected_topic`, `error_reasons`.
  - Chỉ tập trung sinh duy nhất 1 ý tưởng mới thay thế cho dòng `row_id` đó, tránh lặp lại lỗi cũ.
  - Sau khi xong, gửi lại cho Cloudflare kiểm tra. Cloudflare xử lý xong tác vụ này mới chuyển sang tác vụ kế tiếp.

---

### 📁 Workflow 2: `Render.yml` (Kết Xuất Đồ Họa Manim)
* **Đầu vào:** Các dòng có trạng thái `Pending` trên Google Sheet.
* **Quy trình thực thi:**
  1. Đọc dữ liệu 5 từ vựng, Pinyin, nghĩa tiếng Việt, và Metadata từ Sheet.
  2. Tạo file kịch bản Manim chuẩn tỷ lệ 9:16 (1080x1920, 60fps).
  3. **Cover Frame 0.75s tại `00:00:00`:** Nhúng ảnh bìa High-CTR vào đầu video để các nền tảng (TikTok, Reels, Shorts) tự động bắt thumbnail đẹp.
  4. Gọi `edge-tts` sinh âm thanh phát âm tiếng Trung chuẩn xác, ghép tiếng chuông `ding.mp3` và nhịp `tick.mp3`.
  5. Render ra file MP4 chất lượng cao (`-qh`), upload lên Google Drive vào thư mục lưu trữ vĩnh viễn.
  6. Cập nhật link Google Drive vào Cột K của Sheet và đổi trạng thái sang **`Video`**.
  7. Tự động kích hoạt Workflow 3 (`ProductQC.yml`).

---

### 📁 Workflow 3: `ProductQC.yml` (Kiểm Soát Chất Lượng Video Vật Lý)
* **Đầu vào:** Các dòng có trạng thái `Video` trên Google Sheet.
* **Tiêu chuẩn kiểm định OpenCV & FFprobe:**
  - **Tỷ lệ khung hình:** Đúng chuẩn dọc 9:16 ($1080 \times 1920$).
  - **Khung hình đầu tiên (Frame 00:00):** Độ sáng trung bình $\in [10, 245]$, độ tương phản $\sigma \ge 15.0$ (không bị màn hình đen/trắng xóa).
  - **Độ ổn định của bìa:** Duy trì đồng nhất trong $0.75\text{s}$ đầu tiên.
  - **Luồng âm thanh (Audio Stream):** Có đầy đủ kênh phát âm tiếng Trung, không bị tắt tiếng (mute).
  - **Thời lượng:** Chuẩn Shorts/TikTok ($15\text{s} - 120\text{s}$).
* **Kết quả:**
  - **Đạt 100% tiêu chuẩn:** Đổi trạng thái dòng sang **`Ready`** (Sẵn sàng đăng).
  - **Không đạt:** Đổi sang `QC_Failed`, ghi rõ nguyên nhân vào cột `Notes` và gửi cảnh báo về Telegram.

---

## 4. QUY TRÌNH GATEKEEPER 1 TRÊN CLOUDFLARE (NGUYÊN TẮC RETRY 2 LẦN & DELETE)

Cloudflare Worker đóng vai trò là **Giám khảo độc lập** (sử dụng Agnes AI / Cloudflare Workers AI):

```text
[Kịch bản mới từ GitHub] 
       ⬇️
[Gatekeeper 1 Chấm Điểm]
   ├── ✅ ĐẠT CHUẨN ➔ Ghi Google Sheet ➔ Set 'Pending'
   └── ❌ VI PHẠM:
         ├── Lần 1: Gọi GitHub Step 2 viết lại dòng đó (Retry 1)
         ├── Lần 2: Gọi GitHub Step 2 viết lại dòng đó (Retry 2)
         └── Lần 3: DELETE TOÀN BỘ DÒNG CŨ KHỎI GOOGLE SHEET 
                    (Bảo toàn tính độc lập của Gatekeeper, không tự viết đè)
```

### 📋 Tiêu chuẩn chấm điểm nghiêm ngặt của Gatekeeper 1:
1. **100% Chữ Giản Thể:** Không được chứa bất kỳ chữ Phồn thể nào.
2. **Chỉ Dùng 1 Chủ Đề Đơn (Single Topic Only):** Tuyệt đối cấm chủ đề ghép có từ nối (`&`, `VÀ`, `+`, `/`).
3. **100% Nghĩa Tiếng Việt:** Tuyệt đối cấm nghĩa dính tiếng Anh (`chair`, `table`, `window`...).
4. **Pinyin Chuẩn Xác:** Đầy đủ dấu thanh điệu, số âm tiết Pinyin khớp chính xác 1-1 với số chữ Hán.
5. **Chống Trùng Lặp Cặp Từ:** Không trùng $\ge 2$ từ với bất kỳ video nào đã có trong lịch sử Google Sheet.

---

## 5. LỊCH XUẤT BẢN TỰ ĐỘNG (PUBLISHING PIPELINE 3 CA/NGÀY)

Chạy tự động bằng Cloudflare Cron Triggers:
* **Ca 1 (07:00 Sáng GMT+7 / 00:00 UTC):** Lấy đúng 1 video `Ready` trên cùng ➔ Gọi Buffer API đăng ngay lên TikTok, Shorts, Facebook Reels ➔ Set `Published`.
* **Ca 2 (13:00 Chiều GMT+7 / 06:00 UTC):** Lấy đúng 1 video `Ready` tiếp theo ➔ Gọi Buffer API đăng ngay ➔ Set `Published`.
* **Ca 3 (19:00 Tối GMT+7 / 12:00 UTC):** Lấy đúng 1 video `Ready` tiếp theo ➔ Gọi Buffer API đăng ngay ➔ Set `Published`.

$$\text{Tổng tuần} = 3 \text{ video/ngày} \times 7 \text{ ngày} = 21 \text{ video/tuần}$$
Kho 30 dòng được sản xuất vào sáng thứ 7 luôn đảm bảo có sẵn **9 video gối đầu dự phòng**, đảm bảo kênh không bao giờ bị đứt đoạn nội dung.

---

## 6. DANH MỤC CÁC FILE CẦN TRIỂN KHAI & NÂNG CẤP

| Tên File | Vị trí | Nhiệm vụ chính |
| :--- | :--- | :--- |
| `.github/workflows/ScriptNewIdeation.yml` | GitHub Actions | Chứa 2 steps: Step 1 sinh 30 ideas (60s delay, xoay vòng 6 keys) & Step 2 sinh lại dòng lỗi |
| `.github/workflows/Render.yml` | GitHub Actions | Render Manim 1080x1920, nhúng bìa 0.75s, upload Drive, set `Video` |
| `.github/workflows/ProductQC.yml` | GitHub Actions | Quét OpenCV chất lượng video, set `Ready` |
| `cloudflare/src/index.js` | Cloudflare Worker | Webhook nhận kịch bản từ GitHub, Cron 3 ca đăng bài, Webhook Telegram |
| `cloudflare/src/gatekeeper.js` | Cloudflare Worker | Module Gatekeeper 1 chấm điểm, đếm retry, xóa dòng nếu vi phạm lần 3 |
| `scripts/generate_daily_batches.py` | Python Script | Script chạy trên runner US gọi Gemini 3.7 Flash sinh ý tưởng |
