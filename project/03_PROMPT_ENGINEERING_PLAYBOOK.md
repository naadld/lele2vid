# 🧠 CẨM NANG THIẾT KẾ PROMPT AI TỰ ĐỘNG HÓA (PROMPT PLAYBOOK)
## Bí quyết sinh nội dung chất lượng cao, không trùng lặp và 100% không lỗi JSON

---

## 🎯 4 NGUYÊN TẮC VÀNG CHO AI IDEATION

### 1. Nguyên Tắc Cấp Bậc (Hierarchy of Fallbacks)
Khi gọi AI trên Cloudflare Worker, không bao giờ phụ thuộc vào 1 nhà cung cấp duy nhất. Luôn thiết kế cơ chế xoay vòng:
```text
Google AI Studio (Gemini 2.5/2.0) ➔ Agnes AI (GPT-4o mini/DeepSeek) ➔ Cloudflare AI (Llama 3.3) ➔ Built-in Vocab Bank
```

### 2. Nguyên Tắc Chống Trùng Lặp (Spaced Repetition & Anti-Duplication)
Trước khi gọi AI sinh ý tưởng mới, hệ thống tự động đọc lịch sử từ Google Sheets:
* **Lịch sử 10 chủ đề gần nhất**: Chặn không cho AI sinh trùng chủ đề.
* **Lịch sử 50 từ vựng gần nhất**: Chặn không cho AI dùng lại từ trong 5 video gần đây.
* **Quy tắc lặp lại ngắt quãng**: Cho phép tối đa 1 từ cũ (từ hơn 5 video trước để ôn tập), 4/5 từ bắt buộc là từ mới toanh.

### 3. Nguyên Tắc Ràng Buộc Kích Thước Khung Hình (Video-Safe Constraints)
* **Nghĩa tiếng Việt**: Tối đa **30 ký tự** (tuyệt đối không vượt quá 35 ký tự để tránh rớt dòng làm hỏng bố cục video dọc 9:16).
* **Phiên âm (Pinyin / IPA)**: Bắt buộc mỗi âm tiết tương ứng 1 chữ cái/từ và cách nhau bởi 1 dấu cách để video highlight chính xác từng từ.

### 4. Nguyên Tắc Ép Định Dạng JSON Chuẩn (Zero-Markdown Hallucination)
* Luôn sử dụng `responseMimeType: "application/json"` trong Gemini API.
* Bộ lọc Parser `parseAIResponseJson` nhiều tầng: Tự động lột bỏ dấu ```json```, bóc tách mảng `[ ... ]` hoặc object `{ ... }`.

---

## 📝 MẪU PROMPT CHUẨN THEO TỪNG NGÔN NGỮ

### 🇨🇳 Mẫu 1: Tiếng Trung (HSK 1 - HSK 6)
```text
Bạn là chuyên gia sư phạm tiếng Trung cho kênh TikTok/YouTube Shorts "Lê Lê Học Tiếng Trung".
Nhiệm vụ: Tạo 1 bộ chủ đề từ vựng HSK 1 - HSK 3 hấp dẫn, vui tươi, thiết thực.

QUY TẮC:
1. Mỗi bộ gồm đúng 5 từ vựng tiếng Trung.
2. Không trùng với các chủ đề: [{recentTopicsStr}] và từ vựng: [{recentWordsStr}].
3. Pinyin chuẩn xác, đầy đủ thanh điệu, mỗi chữ Hán cách nhau 1 dấu cách (ví dụ: '公共汽车' -> 'gōng gòng qì chē').
4. Nghĩa tiếng Việt ngắn gọn dưới 30 ký tự.
5. Toàn bộ chữ Hán là chữ Giản thể (Simplified Chinese).
6. Phản hồi DUY NHẤT một chuỗi JSON hợp lệ.
```

### 🇬🇧 Mẫu 2: Tiếng Anh (English Vocabulary & Idioms)
```text
Bạn là chuyên gia sư phạm tiếng Anh cho kênh "Lê Lê Học Tiếng Anh".
Nhiệm vụ: Tạo 1 bộ chủ đề từ vựng tiếng Anh giao tiếp / Oxford 3000 / IELTS.

QUY TẮC:
1. Mỗi bộ gồm đúng 5 từ vựng / cụm từ.
2. Không trùng với các chủ đề và từ vựng gần đây.
3. Phiên âm chuẩn IPA quốc tế (ví dụ: 'schedule' -> '/ˈʃedʒ.uːl/').
4. Nghĩa tiếng Việt ngắn gọn dưới 30 ký tự.
5. Cấp độ: A1, A2, B1, B2, C1.
6. Phản hồi DUY NHẤT một chuỗi JSON hợp lệ.
```

### 🇫🇷 Mẫu 3: Tiếng Pháp (Vocabulaire Français)
```text
Bạn là giáo viên tiếng Pháp cho kênh "Lê Lê Học Tiếng Pháp".
Nhiệm vụ: Tạo 1 bộ chủ đề từ vựng tiếng Pháp thực tế (DELF A1 - B2).

QUY TẮC:
1. Mỗi bộ gồm đúng 5 từ vựng.
2. Danh từ bắt buộc có mạo từ đi kèm để phân biệt giống đực/cái (un/une/le/la).
3. Phiên âm IPA chuẩn xác tiếng Pháp.
4. Nghĩa tiếng Việt súc tích dưới 30 ký tự.
5. Phản hồi DUY NHẤT một chuỗi JSON hợp lệ.
```
