/**
 * LeLe Hoc Tieng Trung - Cloudflare Serverless Automation Pipeline
 * 
 * Part A: Manual Telegram Controls & Human-In-The-Loop Moderation:
 * - /help: Detailed guide
 * - /ideate: Generates exactly 1 idea batch (Status: "Pending")
 * - /render: Dispatches GitHub Actions to render all "Pending" rows -> "Video"
 * - /publish: Posts exactly 1 video (priority: "Error" retries -> first "Ready" from top)
 * - /status: Stats of Pending, Video (chờ duyệt), Ready (đã duyệt), Error
 * - Callback Queries:
 *   • Approve ➔ Status: "Ready"
 *   • Reset ➔ Status: "Pending"
 *   • Delete ➔ Status: "Deleted"
 *   • Cancel ➔ Status: "Video"
 * 
 * Part B: Scheduled Automation:
 * 1. 01:00 AM VN (UTC 18:00): Production Cron (Sinh idea Pending -> Kích hoạt GitHub Action render -> Video lên GDrive -> Bắn Telegram kiểm duyệt).
 * 2. 07:00 AM VN (UTC 00:00) & 13:00 PM VN (UTC 06:00): Publishing Cron (Retry tất cả Error -> Đăng 1 video Ready).
 */

import { getConfig } from "./config.js";
import { GoogleSheetsClient } from "./google_sheets.js";
import { generateBatchesWithMultiAI, formatTopicsToSheetRows } from "./ai_ideation.js";
import { triggerGitHubRenderWorkflow } from "./github_trigger.js";
import { publishBatchToBuffer } from "./buffer_publisher.js";
import { sendTelegramMessage, answerTelegramCallback, editTelegramMessageCaption, getHelpMessage } from "./telegram.js";

export default {
  /**
   * HTTP Request Handler (Telegram Webhook & REST Endpoints)
   */
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const config = getConfig(env);

    // 1. Health check / Root
    if (request.method === "GET" && url.pathname === "/") {
      return new Response(JSON.stringify({
        project: "LeLe Hoc Tieng Trung - Cloudflare AI Automation",
        status: "Online (100% Serverless)",
        cron_schedules: [
          "01:00 AM VN (UTC 18:00) - Production & Moderation Pipeline",
          "07:00 AM VN (UTC 00:00) - Publishing Batch 1",
          "13:00 PM VN (UTC 06:00) - Publishing Batch 2"
        ],
        model: config.geminiModel
      }, null, 2), {
        headers: { "Content-Type": "application/json" }
      });
    }

    // 2. Status Endpoint
    if (url.pathname === "/api/status") {
      try {
        const gsheet = new GoogleSheetsClient(
          config.gcpClientEmail,
          config.gcpPrivateKey,
          config.spreadsheetId,
          config.sheetTabName
        );
        const summary = await gsheet.getStatusSummary();
        return new Response(JSON.stringify(summary, null, 2), {
          headers: { "Content-Type": "application/json" }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // 3. Debug AI Endpoint
    if (url.pathname === "/api/debug-ai") {
      const debugLogs = [];
      const originalLog = console.log;
      const originalWarn = console.warn;
      console.log = (...args) => debugLogs.push("[LOG] " + args.join(" "));
      console.warn = (...args) => debugLogs.push("[WARN] " + args.join(" "));

      try {
        const { generateBatchesWithMultiAI } = await import("./ai_ideation.js");
        const res = await generateBatchesWithMultiAI(env, config, {}, 1);
        console.log = originalLog;
        console.warn = originalWarn;
        return new Response(JSON.stringify({
          geminiKeysCount: config.geminiApiKeys?.length || 0,
          agnesKeysCount: config.agnesApiKeys?.length || 0,
          provider: res.provider,
          result: res,
          logs: debugLogs
        }, null, 2), { headers: { "Content-Type": "application/json" } });
      } catch (err) {
        console.log = originalLog;
        console.warn = originalWarn;
        return new Response(JSON.stringify({ error: err.message, stack: err.stack, logs: debugLogs }, null, 2), { status: 500, headers: { "Content-Type": "application/json" } });
      }
    }

    // 4. Manual Ideation API Endpoint (1 batch)
    if (url.pathname === "/api/ideate" && request.method === "POST") {
      try {
        const result = await handleIdeateSingleBatch(env, config);
        return new Response(JSON.stringify(result, null, 2), {
          headers: { "Content-Type": "application/json" }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // 4. Manual Publish API Endpoint (1 batch)
    if (url.pathname === "/api/publish" && request.method === "POST") {
      try {
        const result = await handlePublishSingleBatch(env, config, "Manual API");
        return new Response(JSON.stringify(result, null, 2), {
          headers: { "Content-Type": "application/json" }
        });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message }), { status: 500 });
      }
    }

    // 5. Telegram Webhook Endpoint
    if (url.pathname === "/webhook" && request.method === "POST") {
      if (config.telegramWebhookSecret) {
        const secretHeader = request.headers.get("X-Telegram-Bot-Api-Secret-Token");
        if (secretHeader !== config.telegramWebhookSecret) {
          return new Response("Unauthorized", { status: 401 });
        }
      }

      try {
        const update = await request.json();
        ctx.waitUntil(handleTelegramUpdate(update, env, config));
        return new Response("OK", { status: 200 });
      } catch (err) {
        console.error("Error processing Telegram update:", err);
        return new Response("Bad Request", { status: 400 });
      }
    }

    return new Response("Not Found", { status: 404 });
  },

  /**
   * Scheduled Cron Handler (01:00 AM, 07:00 AM, 13:00 PM VN)
   */
  async scheduled(event, env, ctx) {
    const config = getConfig(env);
    console.log(`[CRON] Scheduled event fired at ${new Date().toISOString()} (Cron: ${event.cron})`);

    ctx.waitUntil(
      (async () => {
        try {
          // 1. Cron 18:00 UTC (01:00 AM VN): Production Schedule
          if (event.cron === "0 18 * * *") {
            await handleProductionCron(env, config);
          } 
          // 2. Cron 00:00 UTC (07:00 AM VN) & 06:00 UTC (13:00 PM VN): Publishing Schedule
          else {
            await handlePublishingCron(env, config);
          }
        } catch (err) {
          console.error("[CRON] Automation execution error:", err);
          await sendTelegramMessage(
            config.telegramBotToken,
            config.telegramChatId,
            `⚠️ <b>[Lỗi Lịch Tự Động]</b>\n\nChi tiết lỗi: <code>${err.message}</code>`
          );
        }
      })()
    );
  }
};

/**
 * Handle Telegram Update & Commands & Moderation Callbacks
 */
async function handleTelegramUpdate(update, env, config) {
  const botToken = config.telegramBotToken;

  // =========================================================================
  // 1. Handle Inline Keyboard Callback Queries (Approve / Reset / Delete / Cancel)
  // =========================================================================
  if (update.callback_query) {
    const cb = update.callback_query;
    const cbId = cb.id;
    const cbData = cb.data || "";
    const msg = cb.message;
    const chatId = msg?.chat?.id;
    const msgId = msg?.message_id;

    console.log(`Received callback query: ${cbData} from chat ${chatId}`);

    const [action, rowId] = cbData.split(":");
    if (!action || !rowId) {
      await answerTelegramCallback(botToken, cbId, "Lệnh không hợp lệ.");
      return;
    }

    const gsheet = new GoogleSheetsClient(
      config.gcpClientEmail,
      config.gcpPrivateKey,
      config.spreadsheetId,
      config.sheetTabName
    );

    const rowInfo = await gsheet.findRowByBatchId(rowId);
    if (!rowInfo) {
      await answerTelegramCallback(botToken, cbId, `Không tìm thấy dòng #${rowId} trên Google Sheet.`, true);
      return;
    }

    let alertText = "";
    let newStatus = "";
    let statusLabel = "";

    // 🟢 Approve -> Ready
    if (action === "approve") {
      newStatus = "Ready";
      statusLabel = "🟢 ĐÃ DUYỆT (Ready - Sẵn sàng đăng tự động)";
      alertText = `Đã duyệt Video #${rowId} (Ready)! Sẵn sàng đăng lúc 07:00 / 13:00.`;
      await gsheet.updateBatchStatus(rowInfo.rowNumber, "Ready");
    }
    // 🔄 Reset -> Pending
    else if (action === "reset") {
      newStatus = "Pending";
      statusLabel = "🔄 ĐÃ RESET (Pending - Chờ render lại)";
      alertText = `Đã chuyển Video #${rowId} về Pending để render lại.`;
      await gsheet.updateBatchStatus(rowInfo.rowNumber, "Pending");
    }
    // 🗑️ Delete -> Deleted
    else if (action === "delete") {
      newStatus = "Deleted";
      statusLabel = "🗑️ ĐÃ XÓA (Deleted)";
      alertText = `Đã xóa dòng Video #${rowId} khỏi hàng đợi.`;
      await gsheet.deleteBatchRow(rowInfo.rowNumber);
    }
    // ⏸️ Cancel -> Keep Video
    else if (action === "cancel") {
      newStatus = "Video";
      statusLabel = "⏸️ ĐÃ HỦY (Giữ nguyên trạng thái Video)";
      alertText = `Đã giữ nguyên trạng thái Video #${rowId} (chưa duyệt).`;
    }

    // Answer callback popup
    await answerTelegramCallback(botToken, cbId, alertText, false);

    // Update message caption to reflect decision
    if (chatId && msgId) {
      const updatedCaption = (
        `🎬 <b>[Kết Quả Kiểm Duyệt] #${rowId}: ${rowInfo.topic}</b>\n\n` +
        `📊 <b>Trạng thái mới:</b> <code>${newStatus}</code>\n` +
        `📌 <b>Quyết định:</b> ${statusLabel}\n` +
        `🕒 <i>Cập nhật lúc: ${new Date().toISOString().substring(0, 16).replace("T", " ")}</i>`
      );
      await editTelegramMessageCaption(botToken, chatId, msgId, updatedCaption, { inline_keyboard: [] });
    }
    return;
  }

  // =========================================================================
  // 2. Handle Text Commands (/start, /help, /ideate, /render, /publish, /status)
  // =========================================================================
  const message = update.message || update.edited_message;
  if (!message || !message.text) return;

  const chatId = message.chat.id;
  const rawText = message.text.trim();
  const command = rawText.split(" ")[0].toLowerCase();

  console.log(`Received command from Chat ${chatId}: ${rawText}`);

  // 1. /help & /start
  if (command === "/start" || command === "/help") {
    await sendTelegramMessage(botToken, chatId, getHelpMessage());
    return;
  }

  // 2. /ideate: Tạo 1 bộ ý tưởng (chỉ 1 dòng) với Status "Pending"
  if (command === "/ideate" || command === "/generate") {
    await sendTelegramMessage(
      botToken,
      chatId,
      `⏳ <b>Đang sinh 1 bộ ý tưởng từ vựng HSK mới...</b>\n<i>(Xoay vòng 6 Google AI Studio + 4 Agnes AI + Cloudflare AI)</i>`
    );

    try {
      const res = await handleIdeateSingleBatch(env, config);
      const msg = `🎉 <b>Đã Tạo 1 Bộ Ý Tưởng Mới!</b>\n\n` +
        `🆔 <b>ID Dòng:</b> #${res.rowId}\n` +
        `📌 <b>Chủ đề:</b> ${res.topic} (${res.level})\n` +
        `🤖 <b>AI Sử Dụng:</b> ${res.provider}\n` +
        `📊 <b>Trạng thái:</b> <code>Pending</code>\n\n` +
        `<i>Dòng đã được thêm vào Google Sheet. Gõ <code>/render</code> khi bạn muốn tạo video!</i>`;
      await sendTelegramMessage(botToken, chatId, msg);
    } catch (err) {
      await sendTelegramMessage(
        botToken,
        chatId,
        `❌ <b>Lỗi Sinh Ý Tưởng:</b>\n<code>${err.message}</code>`
      );
    }
    return;
  }

  // 3. /render: Kích hoạt pipeline render toàn bộ các dòng "Pending" -> "Video"
  if (command === "/render") {
    await sendTelegramMessage(
      botToken,
      chatId,
      `⏳ <b>Đang kích hoạt GitHub Actions để render tất cả dòng Pending...</b>`
    );

    try {
      const ghRes = await triggerGitHubRenderWorkflow(env);
      await sendTelegramMessage(
        botToken,
        chatId,
        `✅ <b>Kích Hoạt GitHub Actions Thành Công!</b>\n\n` +
        `🚀 <b>Tiến trình:</b> ${ghRes.message}\n` +
        `<i>Sau khi video render xong và lưu vào GDrive, hệ thống sẽ bắn video kèm nút kiểm duyệt (Approve/Reset/Delete) trực tiếp vào bot này.</i>`
      );
    } catch (err) {
      await sendTelegramMessage(
        botToken,
        chatId,
        `❌ <b>Lỗi kích hoạt GitHub Action:</b>\n<code>${err.message}</code>`
      );
    }
    return;
  }

  // 4. /publish: Đăng 1 video duy nhất (ưu tiên Error retry -> 1 video Ready từ trên xuống)
  if (command === "/publish") {
    await sendTelegramMessage(
      botToken,
      chatId,
      `⏳ <b>Đang quét video (Error / Ready) & Đăng lên Buffer...</b>`
    );

    try {
      const res = await handlePublishSingleBatch(env, config, "Lệnh /publish thủ công");
      if (res.skipped) {
        await sendTelegramMessage(
          botToken,
          chatId,
          `ℹ️ <b>Thông báo:</b> Không tìm thấy dòng nào có trạng thái <b>Error</b> hoặc <b>Ready</b> để đăng.\n\n` +
          `<i>Lưu ý: Các video mới render cần được bạn bấm <b>Approve</b> trên Telegram để chuyển sang <code>Ready</code> trước khi đăng!</i>`
        );
      } else {
        const isPublished = res.finalStatus === "Published";
        const icon = isPublished ? "✅" : "⚠️";
        const statusText = isPublished ? "<b>Published</b> (Đủ 3 nền tảng)" : "<b>Error</b> (Chưa đủ 3 nền tảng)";

        const msg = `${icon} <b>Kết Quả Đăng Video Buffer:</b>\n\n` +
          `🎬 <b>Video ID:</b> #${res.batchId}\n` +
          `📌 <b>Chủ đề:</b> ${res.topic}\n` +
          `📊 <b>Trạng thái cập nhật:</b> ${statusText}\n\n` +
          `🌐 <b>Chi tiết các nền tảng:</b>\n` +
          `• YouTube: ${res.isYtOk ? "✅ Thành công" : "❌ Chưa đăng"}\n` +
          `• TikTok: ${res.isTtOk ? "✅ Thành công" : "❌ Chưa đăng"}\n` +
          `• Facebook: ${res.isFbOk ? "✅ Thành công" : "❌ Chưa đăng"}\n\n` +
          `<i>${isPublished ? "Video đã đăng tải thành công lên tất cả các kênh!" : "Những kênh chưa đăng sẽ được tự động retry trong lần chạy tiếp theo."}</i>`;
        await sendTelegramMessage(botToken, chatId, msg);
      }
    } catch (err) {
      await sendTelegramMessage(
        botToken,
        chatId,
        `❌ <b>Lỗi Đăng Video:</b>\n<code>${err.message}</code>`
      );
    }
    return;
  }

  // 5. /status: Thống kê Pending, Video, Ready, Error
  if (command === "/status") {
    try {
      const gsheet = new GoogleSheetsClient(
        config.gcpClientEmail,
        config.gcpPrivateKey,
        config.spreadsheetId,
        config.sheetTabName
      );
      const summary = await gsheet.getStatusSummary();

      let errorDetailText = "";
      if (summary.errorCount > 0) {
        errorDetailText = `\n\n⚠️ <b>Chi tiết dòng bị Error:</b>\n` +
          summary.errorDetails.map(d => `• ${d.rowId} (${d.topic}): Thiếu [${d.missingChannels}]`).join("\n");
      }

      const msg = `📊 <b>THỐNG KÊ TRẠNG THÁI VIDEO TRÊN GOOGLE SHEETS</b>\n\n` +
        `💡 <b>Ý tưởng đã sinh (chờ render):</b> <code>${summary.pendingCount}</code> Pending\n` +
        `⏳ <b>Video đã sinh (chờ kiểm duyệt):</b> <code>${summary.videoCount}</code> Video\n` +
        `🟢 <b>Video đã duyệt (sẵn sàng đăng):</b> <code>${summary.readyCount}</code> Ready\n` +
        `⚠️ <b>Video bị lỗi / thiếu kênh:</b> <code>${summary.errorCount}</code> Error` +
        errorDetailText +
        `\n\n<i>Tab: <code>${config.sheetTabName}</code></i>`;
      await sendTelegramMessage(botToken, chatId, msg);
    } catch (err) {
      await sendTelegramMessage(
        botToken,
        chatId,
        `❌ <b>Lỗi đọc trạng thái Sheet:</b>\n<code>${err.message}</code>`
      );
    }
    return;
  }
}

/**
 * Handle Ideation for Exactly 1 Batch (1 row with status "Pending")
 */
export async function handleIdeateSingleBatch(env, config) {
  const gsheet = new GoogleSheetsClient(
    config.gcpClientEmail,
    config.gcpPrivateKey,
    config.spreadsheetId,
    config.sheetTabName
  );

  // 1. Get vocabulary history for smart anti-duplication
  const vocabHistory = await gsheet.getVocabHistory();
  const allRows = await gsheet.getSheetValues(`${config.sheetTabName}!A2:A500`);
  const currentMaxId = allRows.length;

  // 2. Generate 1 topic via Multi-AI rotation (count = 1)
  const { topics: generatedTopics, provider: providerUsed } = await generateBatchesWithMultiAI(
    env,
    config,
    vocabHistory,
    1
  );

  // 3. Format 1 row with Status = "Pending"
  const sheetRows = formatTopicsToSheetRows(generatedTopics, providerUsed, currentMaxId + 1);
  await gsheet.appendRows(sheetRows);

  const topicObj = generatedTopics[0] || {};
  return {
    success: true,
    rowId: currentMaxId + 1,
    topic: topicObj.topic || `Chủ Đề #${currentMaxId + 1}`,
    level: topicObj.level || "HSK 1-2",
    provider: providerUsed
  };
}

/**
 * Handle Publishing Exactly 1 Batch (Prioritizes "Error" then "Ready" from top to bottom)
 */
export async function handlePublishSingleBatch(env, config, source = "Manual") {
  const gsheet = new GoogleSheetsClient(
    config.gcpClientEmail,
    config.gcpPrivateKey,
    config.spreadsheetId,
    config.sheetTabName
  );

  // 1. Find batches with status 'Error' first
  let targetBatches = await gsheet.getBatchesByStatus("Error");

  // 2. If no Error batches, find batches with status 'Ready'
  if (targetBatches.length === 0) {
    targetBatches = await gsheet.getBatchesByStatus("Ready");
  }

  if (targetBatches.length === 0) {
    return { skipped: true, message: "No Error or Ready batches found to publish." };
  }

  // Pick the first batch from top to bottom
  const batch = targetBatches[0];

  // 3. Call Buffer GraphQL API to publish missing platforms
  const publishRes = await publishBatchToBuffer(env, batch);

  // 4. Update Google Sheet status & channels
  await gsheet.updateSocialPublishStatus(batch.rowNumber, publishRes.finalStatus, {
    youtube: publishRes.youtubeStatus,
    tiktok: publishRes.tiktokStatus,
    facebook: publishRes.fbStatus
  });

  const isYtOk = publishRes.youtubeStatus && publishRes.youtubeStatus.toLowerCase().startsWith("pub");
  const isTtOk = publishRes.tiktokStatus && publishRes.tiktokStatus.toLowerCase().startsWith("pub");
  const isFbOk = publishRes.fbStatus && publishRes.fbStatus.toLowerCase().startsWith("pub");

  return {
    success: true,
    batchId: batch.id,
    topic: batch.topic,
    finalStatus: publishRes.finalStatus,
    isYtOk,
    isTtOk,
    isFbOk,
    youtubeStatus: publishRes.youtubeStatus,
    tiktokStatus: publishRes.tiktokStatus,
    fbStatus: publishRes.fbStatus,
    results: publishRes.results,
    errors: publishRes.errors
  };
}

/**
 * Production Cron: Runs at 01:00 AM VN (UTC 18:00)
 * Generates Idea (Pending) -> Triggers GitHub Actions Render -> Produces Video -> Telegram Moderation
 */
export async function handleProductionCron(env, config) {
  const gsheet = new GoogleSheetsClient(
    config.gcpClientEmail,
    config.gcpPrivateKey,
    config.spreadsheetId,
    config.sheetTabName
  );

  const pendingBatches = await gsheet.getBatchesByStatus("Pending");
  const nowStr = new Date().toISOString().substring(0, 16).replace("T", " ");

  console.log(`[PRODUCTION-CRON] Fired at ${nowStr}. Pending count: ${pendingBatches.length}`);

  let ideaGenerated = null;
  if (pendingBatches.length === 0) {
    console.log("[PRODUCTION-CRON] Generating 1 new idea batch for today...");
    ideaGenerated = await handleIdeateSingleBatch(env, config);
  }

  // Trigger GitHub Actions to render all pending rows
  console.log("[PRODUCTION-CRON] Triggering GitHub Actions render workflow...");
  const ghRes = await triggerGitHubRenderWorkflow(env);

  await sendTelegramMessage(
    config.telegramBotToken,
    config.telegramChatId,
    `🏭 <b>[Lịch Sản Xuất 01:00 Sáng VN]</b>\n\n` +
    (ideaGenerated ? `💡 Đã sinh ý tưởng mới: <b>#${ideaGenerated.rowId} - ${ideaGenerated.topic}</b>\n` : `💡 Đang có <b>${pendingBatches.length}</b> ý tưởng Pending.\n`) +
    `🚀 <b>Đã kích hoạt GitHub Actions Render Video!</b>\n` +
    `<i>Khi render xong, video sẽ được gửi kèm nút kiểm duyệt (Approve / Reset / Delete) để bạn duyệt trước khi đăng lúc 07:00 & 13:00.</i>`
  );
}

/**
 * Publishing Cron: Runs at 07:00 AM VN (UTC 00:00) and 13:00 PM VN (UTC 06:00)
 * Handles Error retries (2 attempts max) + Publishes 1 Ready video
 */
export async function handlePublishingCron(env, config) {
  const gsheet = new GoogleSheetsClient(
    config.gcpClientEmail,
    config.gcpPrivateKey,
    config.spreadsheetId,
    config.sheetTabName
  );

  const errorBatches = await gsheet.getBatchesByStatus("Error");
  const readyBatches = await gsheet.getBatchesByStatus("Ready");
  const nowStr = new Date().toISOString().substring(0, 16).replace("T", " ");

  console.log(`[PUBLISHING-CRON] Fired at ${nowStr}. Found ${errorBatches.length} Error and ${readyBatches.length} Ready batches.`);

  // 1. Quét và thử lại (retry tối đa 2 lần) cho TẤT CẢ các dòng Error
  if (errorBatches.length > 0) {
    console.log(`[PUBLISHING-CRON] Retrying ${errorBatches.length} Error batches...`);
    for (const errBatch of errorBatches) {
      // Retry lần 1
      let res = await publishBatchToBuffer(env, errBatch);
      // Nếu vẫn còn lỗi -> Retry lần 2
      if (res.finalStatus === "Error") {
        console.log(`[PUBLISHING-CRON] Error Batch #${errBatch.id} still partial, retrying attempt 2...`);
        res = await publishBatchToBuffer(env, errBatch);
      }

      await gsheet.updateSocialPublishStatus(errBatch.rowNumber, res.finalStatus, {
        youtube: res.youtubeStatus,
        tiktok: res.tiktokStatus,
        facebook: res.fbStatus
      });
    }
  }

  // 2. Đăng ĐÚNG 1 video duy nhất có trạng thái "Ready" (từ trên xuống)
  if (readyBatches.length > 0) {
    const targetVideo = readyBatches[0];
    console.log(`[PUBLISHING-CRON] Publishing 1 Ready video: #${targetVideo.id} - ${targetVideo.topic}...`);
    const res = await publishBatchToBuffer(env, targetVideo);

    await gsheet.updateSocialPublishStatus(targetVideo.rowNumber, res.finalStatus, {
      youtube: res.youtubeStatus,
      tiktok: res.tiktokStatus,
      facebook: res.fbStatus
    });

    const icon = res.finalStatus === "Published" ? "✅" : "⚠️";
    await sendTelegramMessage(
      config.telegramBotToken,
      config.telegramChatId,
      `📢 <b>[Lịch Đăng Tự Động ${nowStr}]</b>\n\n` +
      `${icon} <b>Video:</b> #${targetVideo.id} - ${targetVideo.topic}\n` +
      `📊 <b>Trạng thái:</b> <b>${res.finalStatus}</b>\n` +
      `• YouTube: ${res.isYtOk ? "✅" : "❌"}\n` +
      `• TikTok: ${res.isTtOk ? "✅" : "❌"}\n` +
      `• Facebook: ${res.isFbOk ? "✅" : "❌"}`
    );
  } else {
    // Không có video Ready
    await sendTelegramMessage(
      config.telegramBotToken,
      config.telegramChatId,
      `📢 <b>[Lịch Đăng Tự Động ${nowStr}]</b>\n\n` +
      `⚠️ Không tìm thấy video nào ở trạng thái <b>Ready</b> để đăng bài.\n` +
      `<i>(Vui lòng kiểm tra các video đang ở trạng thái <b>Video</b> và bấm Approve trên Telegram để chuyển sang Ready).</i>`
    );
  }
}
