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
 * Send Moderation Message with Inline Keyboard for human approval
 */
export async function sendModerationVideoMessage(botToken, chatId, batch) {
  if (!botToken || !chatId || !batch) return null;

  const wordsFormatted = (batch.words || []).map((w, idx) => {
    return `   ${idx + 1}. <b>${w.hanzi}</b> (${w.pinyin}): ${w.meaning}`;
  }).join("\n");

  const caption = `🎬 <b>[VIDEO MỚI HOÀN TẤT - CHỜ DUYỆT]</b>\n\n` +
    `🆔 <b>ID Dòng:</b> #${batch.id}\n` +
    `📌 <b>Chủ đề:</b> ${batch.topic} (<code>${batch.level}</code>)\n\n` +
    `📚 <b>Danh sách 5 từ vựng:</b>\n${wordsFormatted}\n\n` +
    `🔗 <b>Link Xem Video (GDrive):</b>\n<a href="${batch.videoUrl}">${batch.videoUrl}</a>\n\n` +
    `👉 <i>Vui lòng bấm nút bên dưới để ra quyết định:</i>`;

  const inlineKeyboard = {
    inline_keyboard: [
      [
        { text: "🟢 Duyệt (Ready)", callback_data: `approve:${batch.id}` },
        { text: "🔄 Làm lại (Reset)", callback_data: `reset:${batch.id}` }
      ],
      [
        { text: "🗑️ Xóa (Delete)", callback_data: `delete:${batch.id}` },
        { text: "⏸️ Bỏ qua (Cancel)", callback_data: `cancel:${batch.id}` }
      ]
    ]
  };

  return await sendTelegramMessage(botToken, chatId, caption, {
    reply_markup: inlineKeyboard
  });
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
   👉 Tạo <b>1 bộ ý tưởng mới</b> (1 dòng) với trạng thái <b>Pending</b>.

🔹 <code>/render</code>:
   👉 Kích hoạt GitHub Action render tất cả dòng <b>Pending</b> ➔ Tạo video vào GDrive ➔ Gửi video kèm nút kiểm duyệt (Approve/Reset/Delete) lên Telegram ➔ Set trạng thái <b>Video</b>.

🔹 <code>/publish</code>:
   👉 Đăng đúng <b>1 video duy nhất</b> (ưu tiên retry dòng <b>Error</b> thiếu kênh, sau đó đăng dòng <b>Ready</b> đã duyệt).

🔹 <code>/status</code>:
   👉 Thống kê: Pending (chờ render), Video (chờ duyệt), Ready (sẵn sàng đăng), Error (lỗi đăng).

🔹 <code>/help</code>:
   👉 Xem lại hướng dẫn này.

━━━━━━━━━━━━━━━━━━━━━
🕒 <b>LỊCH HOẠT ĐỘNG HÀNG NGÀY:</b>
• <b>01:00 Sáng</b> (UTC 18:00): Tự động sản xuất ý tưởng, render video & gửi kiểm duyệt Telegram.
• <b>07:00 Sáng</b> (UTC 00:00): Tự động retry lỗi Error & đăng 1 video <b>Ready</b> lên 3 nền tảng qua Buffer.
• <b>13:00 Chiều</b> (UTC 06:00): Tự động retry lỗi Error & đăng 1 video <b>Ready</b> tiếp theo lên 3 nền tảng qua Buffer.
━━━━━━━━━━━━━━━━━━━━━`;
}
