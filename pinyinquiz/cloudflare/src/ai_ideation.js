/**
 * Multi-AI Ideation Engine for LeLe Hoc Tieng Trung
 * 
 * Hierarchy:
 * 1. Google AI Studio (6 keys rotating with model fallback)
 * 2. Agnes AI (4 keys rotating, apihub.agnes-ai.com)
 * 3. Cloudflare Workers AI (@cf/meta/llama-3.1-8b-instruct)
 * 4. Built-in High-Quality HSK Vocab Bank (Zero-fail fallback)
 */

import { generateHiddenPinyin } from "./pinyin_helper.js";
import { generateSocialMetadata } from "./metadata_helper.js";

// Built-in verified HSK 1-2 curated topics bank
const BUILTIN_VOCAB_BANK = [
  {
    topic: "HSK 1 • Đồ Ăn Quen Thuộc",
    level: "HSK 1",
    words: [
      { hanzi: "米饭", pinyin: "mǐ fàn", meaning: "Cơm" },
      { hanzi: "面条", pinyin: "miàn tiáo", meaning: "Mì sợi" },
      { hanzi: "苹果", pinyin: "píng guǒ", meaning: "Quả táo" },
      { hanzi: "面包", pinyin: "miàn bāo", meaning: "Bánh mì" },
      { hanzi: "鸡蛋", pinyin: "jī dàn", meaning: "Trứng gà" }
    ]
  },
  {
    topic: "HSK 1 • Đồ Uống Hàng Ngày",
    level: "HSK 1",
    words: [
      { hanzi: "喝水", pinyin: "hē shuǐ", meaning: "Uống nước" },
      { hanzi: "牛奶", pinyin: "niú nǎi", meaning: "Sữa bò" },
      { hanzi: "茶", pinyin: "chá", meaning: "Trà" },
      { hanzi: "咖啡", pinyin: "kā fēi", meaning: "Cà phê" },
      { hanzi: "果汁", pinyin: "guǒ zhī", meaning: "Nước hoa quả" }
    ]
  },
  {
    topic: "HSK 1 • Gia Đình Yêu Thương",
    level: "HSK 1",
    words: [
      { hanzi: "爸爸", pinyin: "bà ba", meaning: "Bố / Ba" },
      { hanzi: "妈妈", pinyin: "mā ma", meaning: "Mẹ" },
      { hanzi: "哥哥", pinyin: "gē ge", meaning: "Anh trai" },
      { hanzi: "姐姐", pinyin: "jiě jie", meaning: "Chị gái" },
      { hanzi: "弟弟", pinyin: "dì di", meaning: "Em trai" }
    ]
  },
  {
    topic: "HSK 1 • Trường Học & Đồ Dùng",
    level: "HSK 1",
    words: [
      { hanzi: "老师", pinyin: "lǎo shī", meaning: "Thầy cô giáo" },
      { hanzi: "学生", pinyin: "xué sheng", meaning: "Học sinh" },
      { hanzi: "同学", pinyin: "tóng xué", meaning: "Bạn học" },
      { hanzi: "书包", pinyin: "shū bāo", meaning: "Cặp sách" },
      { hanzi: "汉语", pinyin: "hàn yǔ", meaning: "Tiếng Hán" }
    ]
  },
  {
    topic: "HSK 1 • Số Đếm & Tiền Tệ",
    level: "HSK 1",
    words: [
      { hanzi: "多少", pinyin: "duō shao", meaning: "Bao nhiêu" },
      { hanzi: "块钱", pinyin: "kuài qián", meaning: "Đồng (tiền)" },
      { hanzi: "太贵", pinyin: "tài guì", meaning: "Quá đắt" },
      { hanzi: "便宜", pinyin: "pián yi", meaning: "Rẻ" },
      { hanzi: "买单", pinyin: "mǎi dān", meaning: "Thanh toán" }
    ]
  },
  {
    topic: "HSK 2 • Phương Tiện Đi Lại",
    level: "HSK 2",
    words: [
      { hanzi: "飞机", pinyin: "fēi jī", meaning: "Máy bay" },
      { hanzi: "火车", pinyin: "huǒ chē", meaning: "Tàu hỏa" },
      { hanzi: "出租车", pinyin: "chū zū chē", meaning: "Xe taxi" },
      { hanzi: "公共汽车", pinyin: "gōng gòng qì chē", meaning: "Xe buýt" },
      { hanzi: "自行车", pinyin: "zì xíng chē", meaning: "Xe đạp" }
    ]
  },
  {
    topic: "HSK 2 • Thời Tiết & Bốn Mùa",
    level: "HSK 2",
    words: [
      { hanzi: "晴天", pinyin: "qíng tiān", meaning: "Trời nắng" },
      { hanzi: "阴天", pinyin: "yīn tiān", meaning: "Trời râm" },
      { hanzi: "下雨", pinyin: "xià yǔ", meaning: "Mưa rơi" },
      { hanzi: "刮风", pinyin: "guā fēng", meaning: "Gió thổi" },
      { hanzi: "下雪", pinyin: "xià xuě", meaning: "Tuyết rơi" }
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
  }
];

function buildSystemPrompt(history = {}, count = 1) {
  const recentWords = Array.isArray(history) ? history : (history.recent5Words || []);
  const recentWordsStr = recentWords.slice(-50).join(", ");
  const recentTopicsStr = (history.recentTopics || []).slice(-10).join(", ");

  return `Bạn là chuyên gia sư phạm tiếng Trung cho kênh TikTok/YouTube Shorts "Lê Lê Học Tiếng Trung".
Nhiệm vụ: Tạo ${count} bộ chủ đề từ vựng HSK 1 - HSK 3 hấp dẫn, vui tươi, thiết thực.

QUY TẮC CHỐNG TRÙNG LẶP & CẤU TRÚC:
1. Mỗi bộ gồm đúng 5 từ vựng tiếng Trung (2-3 chữ Hán/từ).
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
  
  let parsed = null;
  try {
    const arrayMatch = text.match(/\[\s*\{[\s\S]*\}\s*\]/);
    if (arrayMatch) {
      parsed = JSON.parse(arrayMatch[0]);
    } else {
      const objMatch = text.match(/\{[\s\S]*\}/);
      if (objMatch) {
        parsed = [JSON.parse(objMatch[0])];
      } else {
        parsed = JSON.parse(text);
      }
    }
  } catch (err) {
    try {
      parsed = JSON.parse(text);
    } catch (e) {
      return null;
    }
  }

  if (parsed && !Array.isArray(parsed)) {
    parsed = [parsed];
  }
  return parsed;
}

/**
 * 1. Call Google AI Studio
 */
async function callGeminiAPI(apiKey, requestedModel, systemPrompt, userPrompt) {
  const modelCandidates = [
    requestedModel,
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest"
  ].filter(Boolean);

  let lastError = null;

  for (const model of modelCandidates) {
    try {
      const cleanModel = model.replace(/^models\//, "");
      const url = `https://generativelanguage.googleapis.com/v1beta/models/${cleanModel}:generateContent?key=${apiKey}`;

      const response = await fetch(url, {
        method: "POST",
        signal: AbortSignal.timeout(6000),
        headers: {
          "Content-Type": "application/json"
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
      if (parsed && parsed.length > 0) {
        return { data: parsed, modelUsed: cleanModel };
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
    "agnes-2.5-flash"
  ].filter(Boolean);

  let lastError = null;

  for (const model of modelCandidates) {
    try {
      const response = await fetch(url, {
        method: "POST",
        signal: AbortSignal.timeout(5000),
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
      if (parsed && parsed.length > 0) {
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
  if (!env.AI) return null;

  const cfModel = model || "@cf/meta/llama-3.1-8b-instruct";
  const response = await env.AI.run(cfModel, {
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
export async function generateBatchesWithMultiAI(env, config, vocabHistory = {}, count = 1) {
  const systemPrompt = buildSystemPrompt(vocabHistory, count);
  const userPrompt = `Hãy tạo ngay ${count} bộ chủ đề từ vựng HSK 1 - HSK 3 mới nhất dạng JSON chuẩn.`;

  let resultTopics = null;
  let providerUsed = "Fallback VOCAB_BANK";

  // 1. Try Google AI Studio Keys (6 keys rotating)
  if (config.geminiApiKeys && config.geminiApiKeys.length > 0) {
    const shuffledGeminiKeys = [...config.geminiApiKeys].sort(() => 0.5 - Math.random());
    
    for (let i = 0; i < shuffledGeminiKeys.length; i++) {
      const key = shuffledGeminiKeys[i];
      const keyShort = `${key.substring(0, 6)}...${key.substring(key.length - 4)}`;
      try {
        console.log(`[AI-Pool] Trying Google AI Studio (Key ${i + 1}/${shuffledGeminiKeys.length}: ${keyShort})...`);
        const res = await callGeminiAPI(key, config.geminiModel, systemPrompt, userPrompt);
        if (res && Array.isArray(res.data) && res.data.length > 0) {
          resultTopics = res.data.slice(0, count);
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
        if (res && Array.isArray(res.data) && res.data.length > 0) {
          resultTopics = res.data.slice(0, count);
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
      const cfModel = config.aiModel || "@cf/meta/llama-3.1-8b-instruct";
      console.log(`[AI-Pool] Trying Cloudflare Workers AI (${cfModel})...`);
      const cfResult = await callCloudflareAI(env, cfModel, systemPrompt, userPrompt);
      if (cfResult && Array.isArray(cfResult) && cfResult.length > 0) {
        resultTopics = cfResult.slice(0, count);
        providerUsed = `Cloudflare Workers AI (${cfModel})`;
        console.log(`✨ Successfully generated with ${providerUsed}!`);
      }
    } catch (err) {
      console.warn("⚠️ Cloudflare Workers AI failed:", err.message);
    }
  }

  // 4. Fallback to Curated Vocab Bank if all AIs failed
  if (!resultTopics || resultTopics.length === 0) {
    console.log("ℹ️ Using Built-in High Quality Vocab Bank as fallback.");
    const shuffledBank = [...BUILTIN_VOCAB_BANK].sort(() => 0.5 - Math.random());
    resultTopics = shuffledBank.slice(0, count);
    providerUsed = "Fallback VOCAB_BANK";
  }

  // Auto-enrich each word with hidden_pinyin
  const enrichedTopics = resultTopics.map(topicItem => {
    const words = (topicItem.words || []).map(w => {
      const hanzi = w.hanzi || "";
      const pinyin = w.pinyin || "";
      const meaning = w.meaning || "";
      const hidden_pinyin = w.hidden_pinyin || generateHiddenPinyin(pinyin);
      return {
        hanzi,
        pinyin,
        hidden_pinyin,
        meaning
      };
    });

    return {
      topic: topicItem.topic || "HSK 1-2 • Từ Vựng Thông Dụng",
      level: topicItem.level || "HSK 1-2",
      words: words
    };
  });

  return {
    topics: enrichedTopics,
    provider: providerUsed
  };
}

/**
 * Format generated topics into 16-column Google Sheet rows
 */
export function formatTopicsToSheetRows(topics, providerUsed, startId = 1) {
  const rows = [];
  const now = new Date().toISOString().substring(0, 19).replace("T", " ");

  topics.forEach((t, idx) => {
    const rowId = startId + idx;
    const meta = generateSocialMetadata(t.topic, t.level, t.words);
    const metaText = meta.formatted_text || "";

    // Format 5 words into "hanzi | pinyin | hidden_pinyin | meaning"
    const wordCols = [];
    for (let wIdx = 0; wIdx < 5; wIdx++) {
      const w = t.words[wIdx];
      if (w) {
        wordCols.push(`${w.hanzi} | ${w.pinyin} | ${w.hidden_pinyin} | ${w.meaning}`);
      } else {
        wordCols.push("");
      }
    }

    const row = [
      String(rowId),                  // Col A: ID
      t.topic,                        // Col B: Topic
      t.level,                        // Col C: Level
      "Pending",                      // Col D: Status
      wordCols[0] || "",              // Col E: Word 1
      wordCols[1] || "",              // Col F: Word 2
      wordCols[2] || "",              // Col G: Word 3
      wordCols[3] || "",              // Col H: Word 4
      wordCols[4] || "",              // Col I: Word 5
      metaText,                       // Col J: Metadata (Clean formatted text)
      "",                             // Col K: Video (GDrive Link)
      "",                             // Col L: Youtube
      "",                             // Col M: Tiktok
      "",                             // Col N: Facebook
      now,                            // Col O: Created At
      `Sinh bởi: ${providerUsed}`     // Col P: Notes
    ];

    rows.push(row);
  });

  return rows;
}
