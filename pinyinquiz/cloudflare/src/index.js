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
import { triggerGitHubRenderWorkflow, triggerGitHubQCWorkflow } from "./github_trigger.js";
import { publishBatchToBuffer } from "./buffer_publisher.js";
import { generateSocialMetadata } from "./metadata_helper.js";
import { sendTelegramMessage, answerTelegramCallback, editTelegramMessageCaption, editTelegramMessageText, getHelpMessage } from "./telegram.js";

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

    // 3b. Dedicated Gemini Test Endpoint
    if (url.pathname === "/api/test-gemini") {
      const geminiKeys = config.geminiApiKeys || [];
      const testModels = [
        config.geminiModel,
        "gemini-2.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-2.5-pro",
        "gemini-1.5-flash"
      ].filter(Boolean);
      const uniqueModels = [...new Set(testModels)];

      const results = [];

      for (let i = 0; i < geminiKeys.length; i++) {
        const key = geminiKeys[i];
        const keyMasked = `${key.substring(0, 8)}...${key.substring(key.length - 4)}`;
        const keyResult = { keyIndex: i + 1, key: keyMasked, availableModels: [], modelTests: [] };

        // 1. Query available models list from Google
        try {
          const listRes = await fetch(`https://generativelanguage.googleapis.com/v1beta/models?key=${key}`);
          if (listRes.ok) {
            const listData = await listRes.json();
            keyResult.availableModels = (listData.models || [])
              .filter(m => m.supportedGenerationMethods?.includes("generateContent"))
              .map(m => m.name.replace("models/", ""));
          } else {
            const errText = await listRes.text();
            keyResult.listModelsError = `(${listRes.status}): ${errText.substring(0, 150)}`;
          }
        } catch (err) {
          keyResult.listModelsError = err.message;
        }

        // 2. Test generateContent on candidate models
        for (const m of uniqueModels) {
          const cleanModel = m.replace(/^models\//, "");
          const testUrl = `https://generativelanguage.googleapis.com/v1beta/models/${cleanModel}:generateContent?key=${key}`;
          try {
            const genRes = await fetch(testUrl, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                systemInstruction: { parts: [{ text: "Bạn là chuyên gia tiếng Trung." }] },
                contents: [{ role: "user", parts: [{ text: "Tạo 1 bộ từ vựng HSK 1 gồm 5 từ dạng JSON chuẩn: [{\"topic\": \"HSK 1 • Đồ Ăn\", \"level\": \"HSK 1\", \"words\": [{\"hanzi\": \"米饭\", \"pinyin\": \"mǐ fàn\", \"meaning\": \"Cơm\"}]}]" }] }],
                generationConfig: { temperature: 0.7, responseMimeType: "application/json" }
              })
            });

            if (genRes.ok) {
              const genData = await genRes.json();
              const parts = genRes.ok ? (genData.candidates?.[0]?.content?.parts || []) : [];
              const nonThought = parts.filter(p => !p.thought && p.text).map(p => p.text).join("");
              keyResult.modelTests.push({
                model: cleanModel,
                status: genRes.status,
                success: true,
                outputPreview: nonThought.substring(0, 200) || (parts[0]?.text || "").substring(0, 200)
              });
              break; // Found working model for this key
            } else {
              const errBody = await genRes.text();
              keyResult.modelTests.push({
                model: cleanModel,
                status: genRes.status,
                success: false,
                error: errBody.substring(0, 200)
              });
            }
          } catch (err) {
            keyResult.modelTests.push({
              model: cleanModel,
              success: false,
              error: err.message
            });
          }
        }

        results.push(keyResult);
      }

      return new Response(JSON.stringify({ geminiKeysCount: geminiKeys.length, results }, null, 2), {
        headers: { "Content-Type": "application/json" }
      });
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

    // 4b. Preview Publish Payload Endpoint
    if (url.pathname === "/api/test-publish-preview") {
      try {
        const gsheet = new GoogleSheetsClient(
          config.gcpClientEmail,
          config.gcpPrivateKey,
          config.spreadsheetId,
          config.sheetTabName
        );
        const { getBatchMetadata } = await import("./metadata_helper.js");
        const { convertGDriveToDirectUrl, getBufferChannels } = await import("./buffer_publisher.js");

        const allRows = await gsheet.getSheetValues(`${config.sheetTabName}!A1:P5`);
        const sampleRow = allRows[1] || [];
        const words = [];
        for (let wIdx = 4; wIdx <= 8; wIdx++) {
          const wVal = sampleRow[wIdx] || "";
          if (wVal) {
            const parts = wVal.split("|").map(s => s.trim());
            words.push({ hanzi: parts[0] || "", pinyin: parts[1] || "", hidden_pinyin: parts[2] || "", meaning: parts[3] || parts[0] || "" });
          }
        }

        const topic = sampleRow[1] || "HSK 1 • Mẫu";
        const level = sampleRow[2] || "HSK 1";
        const metadataCell = sampleRow[9] || "";
        const rawVideoUrl = sampleRow[10] || "";
        const directVideoUrl = convertGDriveToDirectUrl(rawVideoUrl);
        const meta = getBatchMetadata(metadataCell, topic, level, words);

        let channels = [];
        try {
          channels = await getBufferChannels(config.bufferAccessToken || env.BUFFER_ACCESS_TOKEN || "Bhk_Gab-6Gm44FiruBCtoLJlV7SsuaZmVcTl3pDYRmo");
        } catch (e) {
          channels = [{ error: e.message }];
        }

        return new Response(JSON.stringify({
          batchId: sampleRow[0],
          topic,
          level,
          rawVideoUrl,
          directVideoUrl,
          metaFromCell: Boolean(metadataCell && metadataCell.includes("=== 1. YOUTUBE SHORTS ===")),
          parsedMetadata: meta,
          bufferChannels: channels
        }, null, 2), { headers: { "Content-Type": "application/json" } });
      } catch (err) {
        return new Response(JSON.stringify({ error: err.message, stack: err.stack }), { status: 500, headers: { "Content-Type": "application/json" } });
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
    // 🎬 Render Ngay từ nút /ideate
    else if (action === "render_ideate") {
      alertText = `Đang kích hoạt Render Video #${rowId}...`;
      await answerTelegramCallback(botToken, cbId, alertText, false);
      const ghRes = await triggerGitHubRenderWorkflow(env, { row_id: rowId });
      if (chatId && msgId) {
        const updatedText = (
          `🎬 <b>[Đã Kích Hoạt Render Video] #${rowId}: ${rowInfo.topic}</b>\n\n` +
          `📊 <b>Trạng thái:</b> <code>Pending ➔ In Progress</code>\n` +
          `🚀 <b>GitHub Actions:</b> ${ghRes.success ? "✅ Đã kích hoạt workflow" : "⚠️ " + ghRes.error}\n` +
          `🕒 <i>Khi render xong và lưu vào GDrive, bot sẽ tự động gửi video kèm các nút kiểm duyệt (Approve / Reset / Delete) để bạn duyệt!</i>`
        );
        await editTelegramMessageText(botToken, chatId, msgId, updatedText, { inline_keyboard: [] });
      }
      return;
    }
    // ❌ Cancel từ nút /ideate
    else if (action === "cancel_ideate") {
      alertText = `Đã hủy ý tưởng #${rowId}.`;
      await gsheet.deleteBatchRow(rowInfo.rowNumber);
      await answerTelegramCallback(botToken, cbId, alertText, false);
      if (chatId && msgId) {
        const updatedText = (
          `❌ <b>[Đã Hủy Ý Tưởng] #${rowId}: ${rowInfo.topic}</b>\n\n` +
          `📊 <b>Trạng thái:</b> <code>Đã xóa khỏi hàng đợi (Deleted)</code>\n` +
          `🕒 <i>Cập nhật lúc: ${new Date().toISOString().substring(0, 16).replace("T", " ")}</i>`
        );
        await editTelegramMessageText(botToken, chatId, msgId, updatedText, { inline_keyboard: [] });
      }
      return;
    }

    // Answer callback popup for moderation buttons
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

      if (res.repairedBatches && res.repairedBatches.length > 0) {
        const repText = res.repairedBatches.map(b => `• <b>#${b.rowId}</b>: ${b.topic} (<code>${b.level}</code>) ➔ <code>Pending</code>`).join("\n");
        await sendTelegramMessage(
          botToken,
          chatId,
          `🛠️ <b>[Self-Healing] Đã tự động khôi phục ${res.repairedBatches.length} dòng Failed:</b>\n\n${repText}\n\n<i>Các dòng trên đã được sửa lỗi và đổi về Pending để render!</i>`
        );
      }

      const wordListText = (res.words || []).map((w, i) => `${i + 1}. <b>${w.hanzi}</b> (<code>${w.pinyin}</code>): ${w.meaning}`).join("\n");
      const msg = `🎉 <b>ĐÃ TẠO 1 BỘ Ý TƯỞNG MỚI!</b>\n\n` +
        `🆔 <b>ID Dòng:</b> <code>#${res.rowId}</code>\n` +
        `📌 <b>Chủ đề:</b> <b>${res.topic}</b> (<code>${res.level}</code>)\n` +
        `🤖 <b>AI Sử Dụng:</b> <code>${res.provider}</code>\n` +
        `📊 <b>Trạng thái:</b> <code>Pending</code>\n\n` +
        `📚 <b>Danh sách từ vựng:</b>\n${wordListText}\n\n` +
        `👇 <i>Vui lòng chọn thao tác tiếp theo:</i>`;

      const replyMarkup = {
        inline_keyboard: [
          [
            { text: "🎬 Render", callback_data: `render_ideate:${res.rowId}` },
            { text: "❌ Cancel", callback_data: `cancel_ideate:${res.rowId}` }
          ]
        ]
      };

      await sendTelegramMessage(botToken, chatId, msg, { reply_markup: replyMarkup });
    } catch (err) {
      await sendTelegramMessage(
        botToken,
        chatId,
        `❌ <b>Lỗi Sinh Ý Tưởng:</b>\n<code>${err.message}</code>`
      );
    }
    return;
  }

  // 3. /render: Kích hoạt pipeline render toàn bộ các dòng "Pending" (hoặc dòng cụ thể)
  if (command === "/render") {
    const rawTarget = rawText.split(" ")[1] || "";
    const targetRowId = rawTarget.replace("#", "").trim();

    await sendTelegramMessage(
      botToken,
      chatId,
      targetRowId
        ? `⏳ <b>Đang kích hoạt GitHub Actions để render riêng dòng #${targetRowId}...</b>`
        : `⏳ <b>Đang kích hoạt GitHub Actions để render tất cả dòng Pending...</b>`
    );

    try {
      const ghRes = await triggerGitHubRenderWorkflow(env, { row_id: targetRowId });
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

  // 3b. /qc: Kích hoạt Auto-QC Gatekeeper kiểm tra tất cả dòng "Video" -> "Ready"
  if (command === "/qc" || command === "/autoqc") {
    await sendTelegramMessage(
      botToken,
      chatId,
      `⏳ <b>Đang kích hoạt Auto-QC Gatekeeper trên GitHub Actions...</b>\n<i>(Kiểm tra chữ Giản thể, bố cục tràn khung & âm thanh của các video chưa duyệt)</i>`
    );

    try {
      const ghRes = await triggerGitHubQCWorkflow(env);
      await sendTelegramMessage(
        botToken,
        chatId,
        `✅ <b>Kích Hoạt Auto-QC Thành Công!</b>\n\n` +
        `🚀 <b>Tiến trình:</b> ${ghRes.message}\n` +
        `<i>Hệ thống sẽ tải các video 'Video', mổ xẻ kiểm tra và tự động đổi sang 'Ready' (nếu đạt) hoặc 'Pending' (nếu lỗi). Kết quả chi tiết sẽ báo về bot!</i>`
      );
    } catch (err) {
      await sendTelegramMessage(
        botToken,
        chatId,
        `❌ <b>Lỗi kích hoạt Auto-QC:</b>\n<code>${err.message}</code>`
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

      const failedInfoText = (summary.failedCount > 0)
        ? `\n🛠️ <b>Ý tưởng vi phạm nguyên tắc (chờ tự sửa):</b> <code>${summary.failedCount}</code> Failed`
        : "";

      const msg = `📊 <b>THỐNG KÊ TRẠNG THÁI VIDEO TRÊN GOOGLE SHEETS</b>\n\n` +
        `💡 <b>Ý tưởng đã sinh (chờ render):</b> <code>${summary.pendingCount}</code> Pending\n` +
        `⏳ <b>Video đã sinh (chờ kiểm duyệt):</b> <code>${summary.videoCount}</code> Video\n` +
        `🟢 <b>Video đã duyệt (sẵn sàng đăng):</b> <code>${summary.readyCount}</code> Ready` +
        failedInfoText + `\n` +
        `⚠️ <b>Video bị lỗi đăng Buffer:</b> <code>${summary.errorCount}</code> Error` +
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
  let vocabHistory = {};
  let currentMaxId = 0;

  try {
    vocabHistory = await gsheet.getVocabHistory();
    const allRows = await gsheet.getSheetValues(`${config.sheetTabName}!A2:A500`);
    currentMaxId = allRows.length;
  } catch (e) {
    console.warn(`[GSheet Warning] Could not fetch sheet history (${e.message}). Proceeding with empty history.`);
  }

  // 1b. Self-Healing Gatekeeper: Scan & Repair any "Failed" rows first
  const repairedBatches = [];
  try {
    const failedRows = await gsheet.getBatchesByStatus(["Failed"]);
    if (failedRows.length > 0) {
      console.log(`[Self-Healing] Found ${failedRows.length} Failed batch(es). Repairing to Pending...`);
      for (const fRow of failedRows) {
        try {
          const { topics: repairedTopicList, provider: repairProvider } = await generateBatchesWithMultiAI(
            env,
            config,
            vocabHistory,
            1
          );
          const rep = repairedTopicList[0];
          if (rep && rep.words && rep.words.length === 5) {
            const metaObj = generateSocialMetadata(fRow.topic, fRow.level, rep.words);
            await gsheet.repairBatchRow(
              fRow.rowNumber,
              fRow.topic,
              fRow.level,
              rep.words,
              metaObj.formatted_text,
              `[Tự động sửa lỗi bằng ${repairProvider} & đổi sang Pending]`
            );
            repairedBatches.push({
              rowId: fRow.id,
              topic: fRow.topic,
              level: fRow.level,
              provider: repairProvider
            });
          }
        } catch (repairErr) {
          console.error(`[Self-Healing Error] Could not repair row #${fRow.id}: ${repairErr.message}`);
        }
      }
    }
  } catch (healScanErr) {
    console.warn(`[Self-Healing Warning] Could not scan for failed batches: ${healScanErr.message}`);
  }

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
    words: topicObj.words || [],
    provider: providerUsed,
    repairedBatches: repairedBatches
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
  // 1. Repair Failed batches if any
  try {
    const failedBatches = await gsheet.getBatchesByStatus("Failed");
    if (failedBatches.length > 0) {
      console.log(`[PRODUCTION-CRON] Found ${failedBatches.length} Failed batch(es). Repairing to Pending...`);
      ideaGenerated = await handleIdeateSingleBatch(env, config);
    } else if (pendingBatches.length === 0) {
      console.log("[PRODUCTION-CRON] Generating 1 new idea batch for today...");
      ideaGenerated = await handleIdeateSingleBatch(env, config);
    }
  } catch (e) {
    console.warn(`[PRODUCTION-CRON] Ideate/Repair warning: ${e.message}`);
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
