/**
 * Telegram Bot API Client & Webhook Command Handler
 */

/**
 * Send HTML message to Telegram Chat
 */
export async function sendTelegramMessage(botToken, chatId, text, options = {}) {
  if (!botToken || !chatId) {
    console.warn("Telegram bot token or chat ID is missing. Notification skipped.");
    return null;
  }

  const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
  const body = {
    chat_id: chatId,
    text: text,
    parse_mode: options.parse_mode || "HTML",
    disable_web_page_preview: options.disable_web_page_preview ?? true,
    ...options
  };

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    return await res.json();
  } catch (err) {
    console.error("Failed to send Telegram message:", err);
    return null;
  }
}

/**
 * Build help / start menu message
 */
export function getHelpMessage() {
  return `🤖 <b>HỆ THỐNG ĐIỀU KHIỂN TỰ ĐỘNG - LÊ LÊ HỌC TIẾNG TRUNG</b>
<i>(Cloudflare Serverless 24/7 - Độc lập 100% VPS)</i>

💡 <b>DANH SÁCH LỆNH ĐIỀU KHIỂN:</b>
━━━━━━━━━━━━━━━━━━━━━
🔹 <code>/ideate</code>:
   👉 Tạo <b>1 bộ ý tưởng mới</b> (1 dòng) với trạng thái <b>Pending</b> vào Google Sheet.

🔹 <code>/render</code>:
   👉 Kích hoạt GitHub Action render tất cả các dòng <b>Pending</b>. Khi render xong và có video trên GDrive, trạng thái chuyển thành <b>Video</b>.

🔹 <code>/publish</code>:
   👉 Đăng đúng <b>1 video duy nhất</b> (quét từ trên xuống: ưu tiên dòng <b>Error</b> còn thiếu kênh, sau đó đến dòng <b>Video</b>).
   • Đủ cả 3 nền tảng (TikTok, Reels, Shorts) ➔ chuyển thành <b>Published</b>.
   • Nếu thiếu kênh nào ➔ giữ trạng thái <b>Error</b> và ghi nhận kênh thành công để lần sau chạy tiếp.

🔹 <code>/status</code>:
   👉 Báo cáo thống kê:
   • Số ý tưởng đã sinh chưa có video (Pending).
   • Số video đã sinh chưa đăng (Video).
   • Số video đang bị lỗi hoặc thiếu kênh (Error).

🔹 <code>/help</code>:
   👉 Xem lại hướng dẫn này.

⏰ <b>LỊCH ĐĂNG TỰ ĐỘNG 2 LẦN/NGÀY (BUFFER):</b>
• <b>07:00 Sáng</b> (UTC 00:00)
• <b>13:00 Chiều</b> (UTC 06:00)
━━━━━━━━━━━━━━━━━━━━━`;
}
