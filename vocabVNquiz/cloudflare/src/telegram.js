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

  if (body.reply_markup === null || body.reply_markup === undefined) {
    delete body.reply_markup;
  }

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
 * Send Video by URL or File to Telegram Chat
 */
export async function sendTelegramVideo(botToken, chatId, videoUrl, caption = "", replyMarkup = null) {
  if (!botToken || !chatId || !videoUrl) return null;

  const url = `https://api.telegram.org/bot${botToken}/sendVideo`;
  const body = {
    chat_id: chatId,
    video: videoUrl,
    caption: caption,
    parse_mode: "HTML",
    supports_streaming: true
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
    if (!data.ok) {
      console.warn("Telegram sendVideo error:", data);
      // Fallback: send as message with link
      return await sendTelegramMessage(botToken, chatId, `${caption}\n\n🔗 <b>Xem Video:</b> ${videoUrl}`, {
        reply_markup: replyMarkup
      });
    }
    return data;
  } catch (err) {
    console.error("Failed to send Telegram video:", err);
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

🔹 <code>/ideate5</code> (hoặc <code>/idea5</code>, <code>/sinh5</code>):
   👉 Tạo ngay <b>5 bộ ý tưởng HSK mới</b> bất kỳ thời điểm nào (khử trùng 100%, lưu vào Sheet với trạng thái <b>Pending</b>).

🔹 <code>/renderall</code>:
   👉 <b>Render toàn diện</b>: Tự động dò và render <b>TẤT CẢ</b> các dòng <b>Pending</b> sang <b>Video</b>, không để sót bất kỳ dòng Pending nào.

🔹 <code>/render [id]</code>:
   👉 Kích hoạt GitHub Action render dòng cụ thể (hoặc tất cả Pending) ➔ Gắn bìa Cover 0.75s ➔ Set trạng thái <b>Video</b>.

🔹 <code>/qcall</code> (hoặc <code>/qc</code>):
   👉 <b>Auto-QC Gatekeeper</b>: Rà soát <b>TOÀN BỘ</b> các dòng có <b>Video</b>, kiểm tra từng frame chữ Hán, ảnh bìa & âm thanh ➔ Tự động duyệt sang <b>Ready</b>.

🔹 <code>/fix</code> hoặc <code>/heal</code>:
   👉 <b>AI Auto-Healing</b>: Tự động sửa các dòng <b>Failed</b> (chuyển Phồn thể ➔ Giản thể, chuẩn hóa Pinyin & tái tạo Metadata) ➔ Đổi sang <b>Pending</b>.

🔹 <code>/resetall</code>:
   👉 Reset toàn bộ các dòng <b>Video</b> về <b>Pending</b> để render lại video có ảnh bìa mới.

🔹 <code>/reset [id]</code>:
   👉 Reset 1 dòng cụ thể về <b>Pending</b> để kết xuất lại.

🔹 <code>/approve [id]</code>:
   👉 Duyệt thủ công 1 dòng sang <b>Ready</b> (Sẵn sàng đăng).

🔹 <code>/publish</code>:
   👉 Đăng đúng <b>1 video duy nhất</b> (ưu tiên retry dòng <b>Error</b>, sau đó đăng dòng <b>Ready</b>).

🔹 <code>/status</code>:
   👉 Thống kê: Pending, Video, Ready, Error, Failed trên Google Sheets.

🔹 <code>/myid</code>:
   👉 Xem Chat ID Telegram và kiểm tra kết nối bot.

🔹 <code>/help</code>:
   👉 Xem lại hướng dẫn này.

🕒 <b>LỊCH HOẠT ĐỘNG TỰ ĐỘNG HÀNG NGÀY:</b>
• <b>01:00 Sáng</b> (UTC 18:00): 🏭 <b>Sản xuất mẻ 1</b>: Sinh ý tưởng & Render video.
• <b>05:00 Sáng</b> (UTC 22:00): 🛡️ <b>Auto-QC Gatekeeper</b>: Quét & duyệt video ➔ <code>Ready</code>.
• <b>07:00 Sáng</b> (UTC 00:00): 🚀 <b>Lịch đăng lần 1</b>: Đăng 1 video <code>Ready</code> lên 3 MXH.
• <b>08:00 Sáng</b> (UTC 01:00): 📊 <b>Báo cáo Dashboard sáng</b>: Thống kê kho, Quota & Kênh.
• <b>10:00 Sáng</b> (UTC 03:00): 🏭 <b>Sản xuất mẻ 2</b>: Sinh ý tưởng & Render video.
• <b>12:00 Trưa</b> (UTC 05:00): 🛡️ <b>Auto-QC Gatekeeper</b>: Quét & duyệt tiếp video ➔ <code>Ready</code>.
• <b>13:00 Chiều</b> (UTC 06:00): 🚀 <b>Lịch đăng lần 2</b>: Đăng 1 video <code>Ready</code> tiếp theo.
• <b>18:01 Chiều</b> (UTC 11:01): 📊 <b>Báo cáo Dashboard tối</b>: Tổng kết tiến độ toàn ngày.
━━━━━━━━━━━━━━━━━━━━━`;
}
