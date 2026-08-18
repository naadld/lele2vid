/**
 * LeLe Hoc Tieng Trung - Cloudflare Serverless Automation Pipeline
 * 
 * Part A: Manual Telegram Controls:
 * - /help: Detailed guide
 * - /ideate: Generates exactly 1 idea batch (Status: "Pending")
 * - /render: Dispatches GitHub Actions to render all "Pending" rows -> "Video"
 * - /publish: Posts exactly 1 video (priority: "Error" retries -> first "Video" from top)
 * - /status: Stats of Pending, Video, Error (excluding Published)
 * 
 * Part B: Scheduled Automation (07:00 AM & 13:00 PM VN):
 * 1. Retries Error rows for missing channels + publishes next Video row.
 * 2. If only Pending rows exist -> Triggers GitHub Action render.
 * 3. If no Pending/Video/Error exist -> Generates 1 new idea row and triggers render.
 */

import { getConfig } from "./config.js";
import { GoogleSheetsClient } from "./google_sheets.js";
import { generateBatchesWithMultiAI, formatTopicsToSheetRows } from "./ai_ideation.js";
import { triggerGitHubRenderWorkflow } from "./github_trigger.js";
import { publishBatchToBuffer } from "./buffer_publisher.js";
import { sendTelegramMessage, getHelpMessage } from "./telegram.js";

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
        cron_schedules: ["07:00 AM VN (UTC 00:00)", "13:00 PM VN (UTC 06:00)"],
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

    // 3. Manual Ideation API Endpoint (1 batch)
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
   * Scheduled Cron Handler (Runs at 07:00 AM VN and 13:00 PM VN)
   */
  async scheduled(event, env, ctx) {
    const config = getConfig(env);
    console.log(`[CRON] Scheduled event fired at ${new Date().toISOString()} (Cron: ${event.cron})`);

    ctx.waitUntil(
      (async () => {
        try {
          await handleScheduledAutomation(env, config);
        } catch (err) {
          console.error("[CRON] Automation execution error:", err);
          await sendTelegramMessage(
            config.telegramBotToken,
            config.telegramChatId,
            `⚠️ <b>[Lỗi Lịch Đăng Tự Động]</b>\n\nChi tiết lỗi: <code>${err.message}</code>`
          );
        }
      })()
    );
  }
};

/**
 * Handle Telegram Update & Commands
 */
async function handleTelegramUpdate(update, env, config) {
  const message = update.message || update.edited_message;
  if (!message || !message.text) return;

  const chatId = message.chat.id;
  const rawText = message.text.trim();
  const command = rawText.split(" ")[0].toLowerCase();
  const botToken = config.telegramBotToken;

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
        `<i>Sau khi video render xong và lưu vào GDrive, trạng thái dòng sẽ tự động chuyển thành <b>Video</b>.</i>`
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

  // 4. /publish: Đăng 1 video duy nhất (quét từ trên xuống: Error trước, sau đó đến Video)
  if (command === "/publish") {
    await sendTelegramMessage(
      botToken,
      chatId,
      `⏳ <b>Đang quét video (Error / Video) & Đăng lên Buffer...</b>`
    );

    try {
      const res = await handlePublishSingleBatch(env, config, "Lệnh /publish thủ công");
      if (res.skipped) {
        await sendTelegramMessage(
          botToken,
          chatId,
          `ℹ️ <b>Thông báo:</b> Không tìm thấy dòng nào có trạng thái <b>Error</b> hoặc <b>Video</b> trên Google Sheet để đăng bài.`
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
          `<i>${isPublished ? "Video đã đăng tải thành công lên tất cả các kênh!" : "Những kênh chưa đăng sẽ được tự động quét lại trong lần chạy tiếp theo."}</i>`;
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

  // 5. /status: Thống kê Pending, Video, Error (Không tính Published)
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
        `💡 <b>Ý tưởng đã sinh (chưa có video):</b> <code>${summary.pendingCount}</code> Pending\n` +
        `🎬 <b>Video đã sinh (chưa đăng):</b> <code>${summary.videoCount}</code> Video\n` +
        `⚠️ <b>Video bị lỗi / chưa đủ 3 kênh:</b> <code>${summary.errorCount}</code> Error` +
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
 * Handle Publishing Exactly 1 Batch (Prioritizes "Error" then "Video" from top to bottom)
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

  // 2. If no Error batches, find batches with status 'Video'
  if (targetBatches.length === 0) {
    targetBatches = await gsheet.getBatchesByStatus("Video");
  }

  // Also support 'Ready' as alias for Video if any exists
  if (targetBatches.length === 0) {
    targetBatches = await gsheet.getBatchesByStatus("Ready");
  }

  if (targetBatches.length === 0) {
    return { skipped: true, message: "No Error or Video batches found to publish." };
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

  return {
    success: true,
    batchId: batch.id,
    topic: batch.topic,
    finalStatus: publishRes.finalStatus,
    isYtOk: publishRes.isYtOk,
    isTtOk: publishRes.isTtOk,
    isFbOk: publishRes.isFbOk,
    results: publishRes.results,
    errors: publishRes.errors
  };
}

/**
 * Automated Cron Workflow (Runs 2 times/day at 07:00 AM & 13:00 PM VN)
 */
export async function handleScheduledAutomation(env, config) {
  const gsheet = new GoogleSheetsClient(
    config.gcpClientEmail,
    config.gcpPrivateKey,
    config.spreadsheetId,
    config.sheetTabName
  );

  const errorBatches = await gsheet.getBatchesByStatus("Error");
  const videoBatches = await gsheet.getBatchesByStatus(["Video", "Ready"]);
  const pendingBatches = await gsheet.getBatchesByStatus("Pending");

  const nowStr = new Date().toISOString().substring(0, 16).replace("T", " ");

  // =========================================================================
  // Case 1: Có dòng Error hoặc Video -> Tiến hành đăng bài lên Buffer
  // =========================================================================
  if (errorBatches.length > 0 || videoBatches.length > 0) {
    console.log(`[CRON] Found ${errorBatches.length} Error batches and ${videoBatches.length} Video batches.`);

    // 1.1. Ưu tiên xử lý các dòng Error trước (retry 1 lần cho các kênh thiếu)
    for (const errBatch of errorBatches) {
      console.log(`[CRON] Retrying Error Batch #${errBatch.id}...`);
      const res = await publishBatchToBuffer(env, errBatch);
      await gsheet.updateSocialPublishStatus(errBatch.rowNumber, res.finalStatus, {
        youtube: res.youtubeStatus,
        tiktok: res.tiktokStatus,
        facebook: res.fbStatus
      });
    }

    // 1.2. Đăng 1 dòng Video kế tiếp lên 3 kênh
    if (videoBatches.length > 0) {
      const targetVideo = videoBatches[0];
      console.log(`[CRON] Publishing next Video Batch #${targetVideo.id}...`);
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
      await sendTelegramMessage(
        config.telegramBotToken,
        config.telegramChatId,
        `📢 <b>[Lịch Đăng Tự Động ${nowStr}]</b>\n\nĐã hoàn tất thử lại các dòng <b>Error</b> còn thiếu kênh.`
      );
    }
    return;
  }

  // =========================================================================
  // Case 2: Chỉ có Pending (chưa có Video/Error) -> Kích hoạt GitHub Actions Render
  // =========================================================================
  if (pendingBatches.length > 0) {
    console.log(`[CRON] No Video/Error ready, found ${pendingBatches.length} Pending batches. Triggering render...`);
    const ghRes = await triggerGitHubRenderWorkflow(env);
    await sendTelegramMessage(
      config.telegramBotToken,
      config.telegramChatId,
      `⏰ <b>[Lịch Đăng Tự Động ${nowStr}]</b>\n\n` +
      `⚠️ Chưa có video sẵn sàng (đang có ${pendingBatches.length} ý tưởng <b>Pending</b>).\n` +
      `🚀 <b>Đã tự động kích hoạt GitHub Actions Render Video!</b>\n` +
      `<i>Sau khi render xong, video sẽ sẵn sàng để đăng trong đợt tiếp theo.</i>`
    );
    return;
  }

  // =========================================================================
  // Case 3: Không có Pending / Video / Error (hết nội dung) -> Tự động sinh 1 Idea mới & Render
  // =========================================================================
  console.log(`[CRON] No Pending/Video/Error found. Auto-generating 1 new idea and triggering render...`);
  const newIdea = await handleIdeateSingleBatch(env, config);
  const ghRes = await triggerGitHubRenderWorkflow(env);

  await sendTelegramMessage(
    config.telegramBotToken,
    config.telegramChatId,
    `⏰ <b>[Lịch Đăng Tự Động ${nowStr}]</b>\n\n` +
    `💡 Hết nội dung sẵn có: Đã tự động sinh 1 bộ ý tưởng mới (<b>#${newIdea.rowId} - ${newIdea.topic}</b>).\n` +
    `🚀 <b>Đã tự động kích hoạt GitHub Actions Render Video!</b>`
  );
}
