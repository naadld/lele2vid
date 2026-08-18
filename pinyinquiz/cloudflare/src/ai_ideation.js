/**
 * Multi-Provider AI Ideation Engine with Key Rotation & Failover
 * 
 * Hierarchy & Rotation Pool:
 * 1. Google AI Studio (6 keys - Format mới x-goog-api-key, gemini-2.5-flash / gemini-3.6-flash / gemini-flash-latest)
 * 2. Agnes AI (4 keys - apihub.agnes-ai.com, agnes-2.0-flash / agnes-2.5-flash)
 * 3. Cloudflare Workers AI (1 native - Llama 3.3 70B)
 * 4. Comprehensive Fallback Vocab Bank (100% Reliability)
 */

import { prepareWordItem } from "./pinyin_helper.js";
import { generateSocialMetadata } from "./metadata_helper.js";

// Comprehensive Fallback Vocabulary Bank (HSK 1 - HSK 3)
export const FALLBACK_VOCAB_BANK = [
  {
    topic: "HSK 1 • Gia Đình & Xưng Hô",
    level: "HSK 1",
    words: [
      { hanzi: "爸爸", pinyin: "bà ba", meaning: "Bố / Ba" },
      { hanzi: "妈妈", pinyin: "mā ma", meaning: "Mẹ" },
      { hanzi: "儿子", pinyin: "ér zi", meaning: "Con trai" },
      { hanzi: "女儿", pinyin: "nǚ ér", meaning: "Con gái" },
      { hanzi: "朋友", pinyin: "péng you", meaning: "Bạn bè" }
    ]
  },
  {
    topic: "HSK 1 • Số Đếm & Thời Gian",
    level: "HSK 1",
    words: [
      { hanzi: "今天", pinyin: "jīn tiān", meaning: "Hôm nay" },
      { hanzi: "明天", pinyin: "míng tiān", meaning: "Ngày mai" },
      { hanzi: "昨天", pinyin: "zuó tiān", meaning: "Hôm qua" },
      { hanzi: "现在", pinyin: "xiàn zài", meaning: "Bây giờ" },
      { hanzi: "点钟", pinyin: "diǎn zhōng", meaning: "Giờ / Tiếng đồng hồ" }
    ]
  },
  {
    topic: "HSK 1 • Địa Điểm & Phương Hướng",
    level: "HSK 1",
    words: [
      { hanzi: "学校", pinyin: "xué xiào", meaning: "Trường học" },
      { hanzi: "医院", pinyin: "yī yuàn", meaning: "Bệnh viện" },
      { hanzi: "商店", pinyin: "shāng diàn", meaning: "Cửa hàng" },
      { hanzi: "北京", pinyin: "běi jīng", meaning: "Bắc Kinh" },
      { hanzi: "中国", pinyin: "zhōng guó", meaning: "Trung Quốc" }
    ]
  },
  {
    topic: "HSK 1 • Đồ Vật Thường Gặp",
    level: "HSK 1",
    words: [
      { hanzi: "桌子", pinyin: "zhuō zi", meaning: "Cái bàn" },
      { hanzi: "椅子", pinyin: "yǐ zi", meaning: "Cái ghế" },
      { hanzi: "衣服", pinyin: "yī fu", meaning: "Quần áo" },
      { hanzi: "杯子", pinyin: "bēi zi", meaning: "Cái cốc / ly" },
      { hanzi: "电脑", pinyin: "diàn nǎo", meaning: "Máy vi tính" }
    ]
  },
  {
    topic: "HSK 1 • Hành Động Thường Ngày",
    level: "HSK 1",
    words: [
      { hanzi: "说话", pinyin: "shuō huà", meaning: "Nói chuyện" },
      { hanzi: "听歌", pinyin: "tīng gē", meaning: "Nghe nhạc" },
      { hanzi: "看书", pinyin: "kàn shū", meaning: "Đọc sách" },
      { hanzi: "写字", pinyin: "xiě zì", meaning: "Viết chữ" },
      { hanzi: "学习", pinyin: "xué xí", meaning: "Học tập" }
    ]
  },
  {
    topic: "HSK 2 • Giao Tiếp Xã Hội",
    level: "HSK 2",
    words: [
      { hanzi: "帮助", pinyin: "bāng zhù", meaning: "Giúp đỡ" },
      { hanzi: "介绍", pinyin: "jiè shào", meaning: "Giới thiệu" },
      { hanzi: "欢迎", pinyin: "huān yíng", meaning: "Hoan nghênh / Chào đón" },
      { hanzi: "回答", pinyin: "huí dá", meaning: "Trả lời" },
      { hanzi: "希望", pinyin: "xī wàng", meaning: "Hy vọng" }
    ]
  },
  {
    topic: "HSK 2 • Cảm Xúc & Tính Cách",
    level: "HSK 2",
    words: [
      { hanzi: "快乐", pinyin: "kuài lè", meaning: "Vui vẻ / Hạnh phúc" },
      { hanzi: "难过", pinyin: "nán guò", meaning: "Buồn bã" },
      { hanzi: "着急", pinyin: "zháo jí", meaning: "Lo lắng / Vội vàng" },
      { hanzi: "聪明", pinyin: "cōng ming", meaning: "Thông minh" },
      { hanzi: "热情", pinyin: "rè qíng", meaning: "Nhiệt tình" }
    ]
  },
  {
    topic: "HSK 2 • Mua Sắm & Ăn Uống",
    level: "HSK 2",
    words: [
      { hanzi: "西瓜", pinyin: "xī guā", meaning: "Dưa hấu" },
      { hanzi: "鸡蛋", pinyin: "jī dàn", meaning: "Trứng gà" },
      { hanzi: "羊肉", pinyin: "yáng ròu", meaning: "Thịt cừu" },
      { hanzi: "牛奶", pinyin: "niú nǎi", meaning: "Sữa bò" },
      { hanzi: "咖啡", pinyin: "kā fēi", meaning: "Cà phê" }
    ]
  }
];

function buildSystemPrompt(history = {}, count = 1) {
  const recentWords = Array.isArray(history) ? history : (history.recent5Words || []);
  const recentWordsStr = recentWords.slice(-50).join(", ");
  const recentTopicsStr = (history.recentTopics || []).slice(-10).join(", ");

  return `Bạn là chuyên gia sư phạm tiếng Trung cho kênh TikTok/YouTube Shorts "Lê Lê Học Tiếng Trung".
Nhiệm vụ: Tạo ${count} bộ chủ đề từ vựng HSK 1 - HSK 3 hấp dẫn, vui tươi, thiết thực.

QUY TẮC CHỐNG TRÙNG LẶP & CẤU TRÚC:
1. Mỗi video gồm đúng 5 từ vựng tiếng Trung (2-3 chữ Hán/từ).
2. KHÔNG ĐƯỢC trùng lặp nguyên bộ 5 từ hoặc trùng chủ đề với các video gần đây: [${recentTopicsStr}].
3. TUYỆT ĐỐI CẤM dùng lại bất kỳ từ nào đã xuất hiện trong 5 video gần nhất: [${recentWordsStr}].
4. ĐƯỢC PHÉP tái sử dụng TỐI ĐA 1 TỪ VỰNG CŨ (từ các video đã đăng cách đây hơn 5 tập để ôn tập kiến thức), còn lại ít nhất 4 từ trong video BẮT BUỘC PHẢI LÀ TỪ MỚI HOÀN TOÀN.
5. Pinyin phải CHUẨN XÁC và có ĐẦY ĐỦ THANH ĐIỆU (ā, á, ǎ, à, ē, é, ě, è, ī, í, ǐ, ì, ō, ó, ǒ, ò, ū, ú, ǔ, ù, ǖ, ǘ, ǚ, ǜ).
6. Nghĩa tiếng Việt ngắn gọn, dễ hiểu.
7. Phản hồi DUY NHẤT một chuỗi JSON hợp lệ không có văn bản thừa ngoài JSON.

CẤU TRÚC JSON MẪU:
[
  {
    "topic": "HSK 1 • Đồ Ăn Quen Thuộc",
    "level": "HSK 1",
    "words": [
      {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm"},
      {"hanzi": "面条", "pinyin": "miàn tiáo", "meaning": "Mì sợi"},
      {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},
      {"hanzi": "面包", "pinyin": "miàn bāo", "meaning": "Bánh mì"},
      {"hanzi": "鸡蛋", "pinyin": "jī dàn", "meaning": "Trứng gà"}
    ]
  }
]`;
}

function parseAIResponseJson(rawText) {
  if (!rawText) return null;
  let text = String(rawText).trim();
  // Strip markdown ```json ... ```
  text = text.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "");
  
  const match = text.match(/\[\s*\{[\s\S]*\}\s*\]/);
  if (match) {
    text = match[0];
  }
  return JSON.parse(text);
}

/**
 * 1. Call Google AI Studio (Format mới: x-goog-api-key Header + system_instruction)
 */
async function callGeminiAPI(apiKey, requestedModel, systemPrompt, userPrompt) {
  const modelCandidates = [
    requestedModel,
    "gemini-2.5-flash",
    "gemini-3.6-flash",
    "gemini-flash-latest"
  ].filter(Boolean);

  let lastError = null;

  for (const model of modelCandidates) {
    try {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`;
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-goog-api-key": apiKey
        },
        body: JSON.stringify({
          system_instruction: {
            parts: [{ text: systemPrompt }]
          },
          contents: [
            {
              role: "user",
              parts: [{ text: userPrompt }]
            }
          ],
          generationConfig: {
            temperature: 0.7,
            responseMimeType: "application/json"
          }
        })
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`(${response.status}): ${errText.substring(0, 150)}`);
      }

      const data = await response.json();
      const rawText = data.candidates?.[0]?.content?.parts?.[0]?.text;
      const parsed = parseAIResponseJson(rawText);
      if (parsed) {
        return { data: parsed, modelUsed: model };
      }
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error("Gemini API call failed");
}

/**
 * 2. Call Agnes AI (apihub.agnes-ai.com)
 */
async function callAgnesAPI(apiKey, baseUrl, requestedModel, systemPrompt, userPrompt) {
  const cleanBase = (baseUrl || "https://apihub.agnes-ai.com/v1").replace(/\/+$/, "");
  const url = `${cleanBase}/chat/completions`;

  const modelCandidates = [
    requestedModel,
    "agnes-2.0-flash",
    "agnes-2.5-flash",
    "agnes-2.5-pro"
  ].filter(Boolean);

  let lastError = null;

  for (const model of modelCandidates) {
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${apiKey}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          model: model,
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt }
          ],
          temperature: 0.7
        })
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`(${response.status}): ${errText.substring(0, 150)}`);
      }

      const data = await response.json();
      const rawText = data.choices?.[0]?.message?.content;
      const parsed = parseAIResponseJson(rawText);
      if (parsed) {
        return { data: parsed, modelUsed: model };
      }
    } catch (err) {
      lastError = err;
    }
  }

  throw lastError || new Error("Agnes AI call failed");
}

/**
 * 3. Call Cloudflare Workers AI
 */
async function callCloudflareAI(env, model, systemPrompt, userPrompt) {
  if (!env.AI) {
    throw new Error("Cloudflare env.AI binding is not available.");
  }

  const response = await env.AI.run(model, {
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt }
    ],
    temperature: 0.7,
    max_tokens: 2048
  });

  let rawOutput = response.response || response.result || "";
  if (typeof rawOutput !== "string") {
    rawOutput = JSON.stringify(rawOutput);
  }
  return parseAIResponseJson(rawOutput);
}

/**
 * Multi-Provider Key Rotation & Failover Orchestrator
 * (6 Google AI Studio + 4 Agnes AI + 1 Cloudflare AI + Vocab Bank)
 */
export async function generateBatchesWithMultiAI(env, config, existingWords = [], count = 5) {
  const systemPrompt = buildSystemPrompt(existingWords, count);
  const userPrompt = `Hãy tạo ngay ${count} bộ chủ đề từ vựng HSK 1 - HSK 2 mới nhất dạng JSON.`;

  let resultTopics = null;
  let providerUsed = "Built-in Vocab Bank";

  // 1. Try Google AI Studio Keys (6 keys rotating)
  if (config.geminiApiKeys && config.geminiApiKeys.length > 0) {
    const shuffledGeminiKeys = [...config.geminiApiKeys].sort(() => 0.5 - Math.random());
    
    for (let i = 0; i < shuffledGeminiKeys.length; i++) {
      const key = shuffledGeminiKeys[i];
      const keyShort = `${key.substring(0, 6)}...${key.substring(key.length - 4)}`;
      try {
        console.log(`[AI-Pool] Trying Google AI Studio (Key ${i + 1}/${shuffledGeminiKeys.length}: ${keyShort})...`);
        const res = await callGeminiAPI(key, config.geminiModel, systemPrompt, userPrompt);
        if (res && Array.isArray(res.data) && res.data.length >= count) {
          resultTopics = res.data;
          providerUsed = `Google AI Studio (${res.modelUsed} - Key #${i + 1})`;
          console.log(`✨ Successfully generated with ${providerUsed}!`);
          break;
        }
      } catch (err) {
        console.warn(`⚠️ Google AI Studio Key #${i + 1} failed: ${err.message}. Rotating to next key...`);
      }
    }
  }

  // 2. Try Agnes AI Keys (4 keys rotating) if Gemini not successful
  if (!resultTopics && config.agnesApiKeys && config.agnesApiKeys.length > 0) {
    const shuffledAgnesKeys = [...config.agnesApiKeys].sort(() => 0.5 - Math.random());

    for (let i = 0; i < shuffledAgnesKeys.length; i++) {
      const key = shuffledAgnesKeys[i];
      const keyShort = `${key.substring(0, 6)}...${key.substring(key.length - 4)}`;
      try {
        console.log(`[AI-Pool] Trying Agnes AI (Key ${i + 1}/${shuffledAgnesKeys.length}: ${keyShort})...`);
        const res = await callAgnesAPI(key, config.agnesBaseUrl, config.agnesModel, systemPrompt, userPrompt);
        if (res && Array.isArray(res.data) && res.data.length >= count) {
          resultTopics = res.data;
          providerUsed = `Agnes AI (${res.modelUsed} - Key #${i + 1})`;
          console.log(`✨ Successfully generated with ${providerUsed}!`);
          break;
        }
      } catch (err) {
        console.warn(`⚠️ Agnes AI Key #${i + 1} failed: ${err.message}. Rotating to next key...`);
      }
    }
  }

  // 3. Try Cloudflare Workers AI if Gemini and Agnes are unavailable
  if (!resultTopics && env.AI) {
    try {
      console.log(`[AI-Pool] Trying Cloudflare Workers AI (${config.aiModel})...`);
      const topics = await callCloudflareAI(env, config.aiModel, systemPrompt, userPrompt);
      if (Array.isArray(topics) && topics.length >= count) {
        resultTopics = topics;
        providerUsed = `Cloudflare Workers AI (${config.aiModel})`;
        console.log(`✨ Successfully generated with ${providerUsed}!`);
      }
    } catch (err) {
      console.warn(`⚠️ Cloudflare Workers AI failed: ${err.message}`);
    }
  }

  // 4. Final Fallback: Built-in Vocab Bank (100% Guarantee)
  if (!resultTopics || resultTopics.length < count) {
    console.log("⚠️ All AI APIs exhausted/failed. Falling back to built-in VOCAB_BANK pools...");
    const shuffled = [...FALLBACK_VOCAB_BANK].sort(() => 0.5 - Math.random());
    resultTopics = shuffled.slice(0, count);
    providerUsed = "Fallback VOCAB_BANK";
  }

  return {
    topics: resultTopics.slice(0, count),
    provider: providerUsed
  };
}

/**
 * Format generated topics into complete Google Sheet rows
 */
export function formatTopicsToSheetRows(topics, providerName = "AI Multi-Provider", startId = 1) {
  const now = new Date();
  const dateStr = now.toISOString().replace("T", " ").substring(0, 19);
  const rows = [];

  for (let i = 0; i < topics.length; i++) {
    const item = topics[i];
    const rowId = String(startId + i);
    const topic = item.topic || `HSK 1-2 • Chủ Đề #${rowId}`;
    const level = item.level || "HSK 1-2";
    const words = item.words || [];

    // Columns: # (1), Topic (2), Level (3), Status (4)
    const row = [rowId, topic, level, "Pending"];
    const parsedWordObjs = [];

    // Word 1 to Word 5 (Columns 5 to 9)
    for (let wIdx = 0; wIdx < 5; wIdx++) {
      const w = words[wIdx] || { hanzi: "", pinyin: "", meaning: "" };
      const wordObj = prepareWordItem(w.hanzi, w.pinyin, w.meaning);
      parsedWordObjs.push(wordObj);
      row.push(wordObj.formatted_cell);
    }

    // Generate Social Metadata preview / text
    const metaObj = generateSocialMetadata(topic, level, parsedWordObjs);
    const metaPreview = `[YouTube]: ${metaObj.youtube.title}\n[TikTok]: ${metaObj.tiktok.caption}`;

    // Col 10: metadata, Col 11: Video, Col 12: Youtube, Col 13: Tiktok, Col 14: Facebook, Col 15: Created At, Col 16: Notes
    row.push(
      metaPreview,
      "", // Video URL (will be populated by GitHub Actions)
      "", // Youtube
      "", // Tiktok
      "", // Facebook
      dateStr, // Created At
      `Sinh bởi: ${providerName}`
    );

    rows.push(row);
  }

  return rows;
}
