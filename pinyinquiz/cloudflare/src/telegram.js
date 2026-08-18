/**
 * Telegram Bot API Client & Webhook Command Handler
 */

/**
 * Send HTML message to Telegram Chat with automatic plain-text fallback
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
    const data = await res.json();
    if (!data.ok) {
      console.warn("Telegram sendMessage error:", data);
      // Fallback: retry with plain text if HTML entity parsing failed
      if (data.description && data.description.includes("parse entities")) {
        const plainText = text.replace(/<[^>]*>/g, "");
        const retryRes = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            chat_id: chatId,
            text: plainText,
            disable_web_page_preview: true
          })
        });
        return await retryRes.json();
      }
    }
    return data;
  } catch (err) {
    console.error("Failed to send Telegram message:", err);
    return null;
  }
}

/**
 * Answer Telegram Callback Query
 */
export async function answerTelegramCallback(botToken, callbackQueryId, text = "", showAlert = false) {
  if (!botToken || !callbackQueryId) return null;

  const url = `https://api.telegram.org/bot${botToken}/answerCallbackQuery`;
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        callback_query_id: callbackQueryId,
        text: text,
        show_alert: showAlert
      })
    });
    return await res.json();
  } catch (err) {
    console.error("Failed to answer callback query:", err);
    return null;
  }
}

/**
 * Edit Telegram Message Caption
 */
export async function editTelegramMessageCaption(botToken, chatId, messageId, caption, replyMarkup = null) {
  if (!botToken || !chatId || !messageId) return null;

  const url = `https://api.telegram.org/bot${botToken}/editMessageCaption`;
  const body = {
    chat_id: chatId,
    message_id: messageId,
    caption: caption,
    parse_mode: "HTML"
  };

  if (replyMarkup !== null) {
    body.reply_markup = replyMarkup;
  }

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!data.ok && data.description && data.description.includes("parse entities")) {
      const plainCaption = caption.replace(/<[^>]*>/g, "");
      const retryRes = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: chatId,
          message_id: messageId,
          caption: plainCaption,
          reply_markup: replyMarkup !== null ? replyMarkup : undefined
        })
      });
      return await retryRes.json();
    }
    return data;
  } catch (err) {
    console.error("Failed to edit message caption:", err);
    return null;
  }
}

/**
 * Edit Telegram Message Text
 */
export async function editTelegramMessageText(botToken, chatId, messageId, text, replyMarkup = null) {
  if (!botToken || !chatId || !messageId) return null;

  const url = `https://api.telegram.org/bot${botToken}/editMessageText`;
  const body = {
    chat_id: chatId,
    message_id: messageId,
    text: text,
    parse_mode: "HTML",
    disable_web_page_preview: true
  };

  if (replyMarkup !== null) {
    body.reply_markup = replyMarkup;
  }

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!data.ok && data.description && data.description.includes("parse entities")) {
      const plainText = text.replace(/<[^>]*>/g, "");
      const retryRes = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: chatId,
          message_id: messageId,
          text: plainText,
          disable_web_page_preview: true,
          reply_markup: replyMarkup !== null ? replyMarkup : undefined
        })
      });
      return await retryRes.json();
    }
    return data;
  } catch (err) {
    console.error("Failed to edit message text:", err);
    return null;
  }
}

/**
 * Build help / start menu message
 */
export function getHelpMessage() {
  return `🤖 <b>HỆ THỐNG ĐIỀU KHIỂN & KIỂM DUYỆT TỰ ĐỘNG - LÊ LÊ HỌC TIẾNG TRUNG</b>
<i>(Cloudflare Serverless 24/7 - Độc lập 100% VPS)</i>

💡 <b>DANH SÁCH LỆNH ĐIỀU KHIỂN:</b>
━━━━━━━━━━━━━━━━━━━━━
🔹 <code>/ideate</code>:
   👉 Tạo <b>1 bộ ý tưởng mới</b> (1 dòng) với trạng thái <b>Pending</b> (kèm nút Render / Cancel).

🔹 <code>/render</code>:
   👉 Kích hoạt GitHub Action render tất cả dòng <b>Pending</b> ➔ Tạo video vào GDrive ➔ Set trạng thái <b>Video</b>.

🔹 <code>/qc</code>:
   👉 Kích hoạt <b>Auto-QC Gatekeeper</b>: Tải và mổ xẻ video để tự động duyệt các dòng <b>Video</b> ➔ <b>Ready</b> (hoặc trả về Pending nếu lỗi).

🔹 <code>/publish</code>:
   👉 Đăng đúng <b>1 video duy nhất</b> (ưu tiên retry dòng <b>Error</b> thiếu kênh, sau đó đăng dòng <b>Ready</b> đã duyệt).

🔹 <code>/status</code>:
   👉 Thống kê: Pending (chờ render), Video (chờ duyệt), Ready (sẵn sàng đăng), Error (lỗi đăng).

🔹 <code>/help</code>:
   👉 Xem lại hướng dẫn này.

━━━━━━━━━━━━━━━━━━━━━
🕒 <b>LỊCH HOẠT ĐỘNG TỰ ĐỘNG HÀNG NGÀY:</b>
• <b>01:00 Sáng</b> (UTC 18:00): Tự động sản xuất ý tưởng, render video & gửi về bot chờ duyệt.
• <b>06:30 Sáng</b> (UTC 23:30): <b>Auto-QC Gatekeeper</b> quét & duyệt tự động video chưa kịp bấm ➔ <code>Ready</code>.
• <b>07:00 Sáng</b> (UTC 00:00): Tự động retry lỗi Error & đăng 1 video <b>Ready</b> lên YouTube, TikTok, Reels.
• <b>12:30 Trưa</b> (UTC 05:30): <b>Auto-QC Gatekeeper</b> quét & duyệt tiếp video còn lại ➔ <code>Ready</code>.
• <b>13:00 Chiều</b> (UTC 06:00): Tự động retry lỗi Error & đăng 1 video <b>Ready</b> tiếp theo.
━━━━━━━━━━━━━━━━━━━━━`;
}
