/**
 * Multi-AI Ideation Engine for LeLe Hoc Tieng Trung
 * 
 * Hierarchy:
 * 1. Google AI Studio (6 keys rotating with model fallback: gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-flash)
 * 2. Agnes AI (4 keys rotating: gpt-4o-mini, gemini-2.5-flash, deepseek-chat)
 * 3. Cloudflare Workers AI (@cf/meta/llama-3.3-70b-instruct, @cf/meta/llama-3.1-8b-instruct, @cf/qwen/qwen2.5-72b-instruct)
 * 4. Built-in High-Quality HSK Vocab Bank (Zero-fail fallback)
 */

import { generateHiddenPinyin } from "./pinyin_helper.js";
import { generateSocialMetadata } from "./metadata_helper.js";

// Built-in verified HSK 1-2 curated topics bank (Fallback)
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
1. Mỗi bộ gồm đúng 5 từ vựng tiếng Trung (1-4 chữ Hán/từ).
2. KHÔNG ĐƯỢC trùng lặp nguyên bộ 5 từ hoặc trùng chủ đề với các video gần đây: [${recentTopicsStr}].
3. TUYỆT ĐỐI CẤM dùng lại bất kỳ từ nào đã xuất hiện trong 5 video gần nhất: [${recentWordsStr}].
4. ĐƯỢC PHÉP tái sử dụng TỐI ĐA 1 TỪ VỰNG CŨ (từ các video đã đăng cách đây hơn 5 tập để ôn tập kiến thức), còn lại ít nhất 4 từ trong video BẮT BUỘC PHẢI LÀ TỪ MỚI HOÀN TOÀN.
5. Pinyin phải CHUẨN XÁC, có ĐẦY ĐỦ THANH ĐIỆU (ā, á, ǎ, à, ē, é, ě, è, ī, í, ǐ, ì, ō, ó, ǒ, ò, ū, ú, ǔ, ù, ǖ, ǘ, ǚ, ǜ) và BẮT BUỘC MỖI CHỮ HÁN PHẢI CÓ ĐÚNG 1 ÂM TIẾT CÁCH NHAU BẰNG DẤU CÁCH (1-to-1 match). Ví dụ: '公共汽车' -> 'gōng gòng qì chē', '自行车' -> 'zì xíng chē', '出租车' -> 'chū zū chē' (TUYỆT ĐỐI KHÔNG viết dính liền 'gōnggòng qìchē' hay 'zìxíngchē').
6. Nghĩa tiếng Việt ngắn gọn, súc tích, TỐI ĐA 30 KÝ TỰ (tuyệt đối không vượt quá 35 ký tự để tránh rớt dòng làm lệch khung video).
7. Toàn bộ chữ Hán BẮT BUỘC là chữ Giản thể (Simplified Chinese).
8. Phản hồi DUY NHẤT một chuỗi JSON hợp lệ không có văn bản thừa ngoài JSON.

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

/**
 * Universal JSON response parser with multi-format normalization
 */
export function parseAIResponseJson(rawText) {
  if (!rawText) return null;
  let text = String(rawText).trim();

  // Strip markdown code fences
  text = text.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "").trim();

  const normalizeResult = (obj) => {
    if (!obj) return null;
    if (Array.isArray(obj)) {
      return obj.filter(item => item && (item.words || item.topic));
    }
    if (typeof obj === "object") {
      if (Array.isArray(obj.topics)) return obj.topics;
      if (Array.isArray(obj.batches)) return obj.batches;
      if (Array.isArray(obj.data)) return obj.data;
      if (Array.isArray(obj.results)) return obj.results;
      if (Array.isArray(obj.words) || obj.topic) return [obj];
      const values = Object.values(obj);
      if (values.length > 0 && values.some(v => v && (v.words || v.topic))) {
        return values.filter(v => v && (v.words || v.topic));
      }
    }
    return null;
  };

  // 1. Direct parse
  try {
    const direct = JSON.parse(text);
    const normalized = normalizeResult(direct);
    if (normalized && normalized.length > 0) return normalized;
  } catch (e) {}

  // 2. Extract JSON Array [ ... ]
  try {
    const arrayMatch = text.match(/\[\s*\{[\s\S]*\}\s*\]/);
    if (arrayMatch) {
      const arr = JSON.parse(arrayMatch[0]);
      const normalized = normalizeResult(arr);
      if (normalized && normalized.length > 0) return normalized;
    }
  } catch (e) {}

  // 3. Extract JSON Object { ... }
  try {
    const objMatch = text.match(/\{[\s\S]*\}/);
    if (objMatch) {
      const obj = JSON.parse(objMatch[0]);
      const normalized = normalizeResult(obj);
      if (normalized && normalized.length > 0) return normalized;
    }
  } catch (e) {}

  return null;
}

/**
 * 1. Call Google AI Studio (Gemini v1beta REST API)
 * Fully compatible with Gemini 2.5 / 2.0 / 1.5 Flash models and multi-part / thinking responses.
 */
async function callGeminiAPI(apiKey, requestedModel, systemPrompt, userPrompt) {
  const rawModel = (requestedModel || "gemini-3.6-flash").trim();
  const modelCandidates = [
    rawModel,
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash"
  ];
  const uniqueModels = [...new Set(modelCandidates.filter(Boolean))];

  let lastError = null;

  for (const model of uniqueModels) {
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
          systemInstruction: {
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
        const err = new Error(`[Model: ${cleanModel}] (${response.status}): ${errText.substring(0, 180)}`);
        // If quota exceeded (429) or invalid key/location error (400), don't waste time trying other sub-models on this same key
        if (response.status === 429 || (response.status === 400 && !errText.includes("not found"))) {
          throw err;
        }
        lastError = err;
        continue;
      }

      const data = await response.json();
      const candidate = data.candidates?.[0];
      const parts = candidate?.content?.parts || [];

      // Separate actual content from thinking parts in Gemini 2.5 / 2.0 / 3.x
      const textParts = parts.filter(p => !p.thought && p.text).map(p => p.text);
      const rawText = textParts.length > 0 
        ? textParts.join("\n") 
        : parts.map(p => p.text || "").join("\n");

      const parsed = parseAIResponseJson(rawText);
      if (parsed && parsed.length > 0) {
        return { data: parsed, modelUsed: cleanModel };
      }
    } catch (err) {
      console.warn(`[Gemini Sub-Candidate] ${err.message}`);
      lastError = err;
      if (err.message.includes("429") || err.message.includes("User location") || err.message.includes("API key not valid")) {
        break; // Rotate to next key immediately
      }
    }
  }

  throw lastError || new Error("Gemini API call failed");
}

/**
 * 2. Call Agnes AI (apihub.agnes-ai.com / OpenAI-compatible API Gateway)
 */
async function callAgnesAPI(apiKey, baseUrl, requestedModel, systemPrompt, userPrompt) {
  const cleanBase = (baseUrl || "https://apihub.agnes-ai.com/v1").replace(/\/+$/, "");
  const url = `${cleanBase}/chat/completions`;

  const rawModel = (requestedModel || "agnes-2.0-flash").trim();
  const modelCandidates = [
    rawModel,
    "agnes-2.0-flash",
    "agnes-2.5-flash",
    "agnes-2.5-pro-alpha"
  ];
  const uniqueModels = [...new Set(modelCandidates.filter(Boolean))];

  let lastError = null;

  for (const model of uniqueModels) {
    try {
      const response = await fetch(url, {
        method: "POST",
        signal: AbortSignal.timeout(8000),
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
        throw new Error(`(${response.status}): ${errText.substring(0, 180)}`);
      }

      const data = await response.json();
      const choice = data.choices?.[0];
      let rawText = choice?.message?.content;

      if (Array.isArray(rawText)) {
        rawText = rawText.map(item => item.text || item.content || "").join("\n");
      } else if (!rawText && choice?.message?.reasoning_content) {
        rawText = choice.message.reasoning_content;
      }

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
 * 3. Call Cloudflare Workers AI (Native binding)
 */
async function callCloudflareAI(env, model, systemPrompt, userPrompt) {
  if (!env.AI) return null;

  const rawModel = (model || "@cf/meta/llama-3.3-70b-instruct").trim();
  const modelCandidates = [
    rawModel,
    "@cf/meta/llama-3.3-70b-instruct",
    "@cf/meta/llama-3.1-8b-instruct",
    "@cf/qwen/qwen2.5-72b-instruct",
    "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"
  ];
  const uniqueModels = [...new Set(modelCandidates.filter(Boolean))];

  for (const cfModel of uniqueModels) {
    try {
      console.log(`[AI-Pool] Trying Cloudflare Workers AI with model: ${cfModel}`);
      const response = await env.AI.run(cfModel, {
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt }
        ],
        temperature: 0.7,
        max_tokens: 2048
      });

      let rawOutput = "";
      if (typeof response === "string") {
        rawOutput = response;
      } else if (response?.response) {
        rawOutput = response.response;
      } else if (response?.result?.response) {
        rawOutput = response.result.response;
      } else if (response?.choices?.[0]?.message?.content) {
        rawOutput = response.choices[0].message.content;
      } else if (response?.text) {
        rawOutput = response.text;
      } else {
        rawOutput = JSON.stringify(response);
      }

      const parsed = parseAIResponseJson(rawOutput);
      if (parsed && parsed.length > 0) {
        return { data: parsed, modelUsed: cfModel };
      }
    } catch (err) {
      console.warn(`⚠️ Cloudflare Workers AI (${cfModel}) failed: ${err.message}`);
    }
  }

  return null;
}

/**
 * Multi-Provider Key Rotation & Failover Orchestrator
 * (Google AI Studio + Agnes AI + Cloudflare Workers AI + Curated Vocab Bank)
 */
export async function generateBatchesWithMultiAI(env, config, vocabHistory = {}, count = 1) {
  const systemPrompt = buildSystemPrompt(vocabHistory, count);
  const userPrompt = `Hãy tạo ngay ${count} bộ chủ đề từ vựng HSK 1 - HSK 3 mới nhất dạng JSON chuẩn.`;

  let resultTopics = null;
  let providerUsed = "Fallback VOCAB_BANK";
  let anyAiSucceeded = false;
  const diagnostics = {
    gemini: [],
    agnes: [],
    cloudflare: []
  };

  // 1. Try Google AI Studio Keys (Rotating pool)
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
          anyAiSucceeded = true;
          console.log(`✨ Successfully generated with ${providerUsed}!`);
          break;
        }
      } catch (err) {
        const cleanErr = (err.message || "Unknown error").substring(0, 180);
        diagnostics.gemini.push(`Key #${i + 1} (${keyShort}): ${cleanErr}`);
        console.warn(`⚠️ Google AI Studio Key #${i + 1} failed: ${cleanErr}. Rotating to next key...`);
      }
    }
  }

  // 2. Try Agnes AI Keys if Gemini not successful
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
          anyAiSucceeded = true;
          console.log(`✨ Successfully generated with ${providerUsed}!`);
          break;
        }
      } catch (err) {
        const cleanErr = (err.message || "Unknown error").substring(0, 180);
        diagnostics.agnes.push(`Key #${i + 1} (${keyShort}): ${cleanErr}`);
        console.warn(`⚠️ Agnes AI Key #${i + 1} failed: ${cleanErr}. Rotating to next key...`);
      }
    }
  }

  // 3. Try Cloudflare Workers AI if Gemini and Agnes are unavailable
  if (!resultTopics && env && env.AI) {
    const cfModel = config.aiModel || "@cf/meta/llama-3.3-70b-instruct";
    try {
      console.log(`[AI-Pool] Trying Cloudflare Workers AI (${cfModel})...`);
      const cfRes = await callCloudflareAI(env, cfModel, systemPrompt, userPrompt);
      if (cfRes && Array.isArray(cfRes.data) && cfRes.data.length > 0) {
        resultTopics = cfRes.data.slice(0, count);
        providerUsed = `Cloudflare Workers AI (${cfRes.modelUsed})`;
        anyAiSucceeded = true;
        console.log(`✨ Successfully generated with ${providerUsed}!`);
      }
    } catch (err) {
      const cleanErr = (err.message || "Unknown error").substring(0, 180);
      diagnostics.cloudflare.push(`CF AI (${cfModel}): ${cleanErr}`);
      console.warn("⚠️ Cloudflare Workers AI failed:", cleanErr);
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
    const rawWords = topicItem.words || [];
    const words = rawWords.map(w => {
      const hanzi = (w.hanzi || "").trim();
      const pinyin = (w.pinyin || "").trim();
      const meaning = (w.meaning || "").trim();
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
    provider: providerUsed,
    isFallbackBank: !anyAiSucceeded,
    diagnostics: diagnostics
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
