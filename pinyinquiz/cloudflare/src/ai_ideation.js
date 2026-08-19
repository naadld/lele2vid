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
import { getVietnamTimestamp } from "./google_sheets.js";

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
    topic: "HSK 2 • Sức Khỏe & Thể Thao",
    level: "HSK 2",
    words: [
      { hanzi: "生病", pinyin: "shēng bìng", meaning: "Bị ốm / Bị bệnh" },
      { hanzi: "发烧", pinyin: "fā shāo", meaning: "Phát sốt" },
      { hanzi: "吃药", pinyin: "chī yào", meaning: "Uống thuốc" },
      { hanzi: "跑步", pinyin: "pǎo bù", meaning: "Chạy bộ" },
      { hanzi: "游泳", pinyin: "yóu yǒng", meaning: "Bơi lội" }
    ]
  },
  {
    topic: "HSK 2 • Mua Sắm & Thanh Toán",
    level: "HSK 2",
    words: [
      { hanzi: "打折", pinyin: "dǎ zhé", meaning: "Giảm giá" },
      { hanzi: "刷卡", pinyin: "shuā kǎ", meaning: "Quẹt thẻ" },
      { hanzi: "现金", pinyin: "xiàn jīn", meaning: "Tiền mặt" },
      { hanzi: "收据", pinyin: "shōu jù", meaning: "Hóa đơn / Biên lai" },
      { hanzi: "找钱", pinyin: "zhǎo qián", meaning: "Trả lại tiền thừa" }
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
  const allUsedWords = Array.isArray(history) ? history : (history.allUsedWords || history.recent5Words || []);
  const allUsedWordsStr = allUsedWords.slice(-150).join(", ");
  const allTopicsStr = (history.allTopics || history.recentTopics || []).slice(-20).join(", ");

  return `Bạn là chuyên gia biên soạn giáo trình HSK cho kênh TikTok/YouTube Shorts "Lê Lê Học Tiếng Trung".
Nhiệm vụ: Tạo ${count} bộ chủ đề từ vựng HSK 1, HSK 2 hoặc HSK 3 hấp dẫn, sinh động, giàu tính ứng dụng thực tế.

QUY TẮC CHỐNG TRÙNG LẶP & ĐA DẠNG HÓA TỪ VỰNG:
1. Mỗi bộ gồm đúng 5 từ vựng tiếng Trung (từ 1 đến 4 chữ Hán mỗi từ).
2. TUYỆT ĐỐI CẤM trùng lặp các chủ đề đã có trên kênh: [${allTopicsStr}]. Hãy sáng tạo các chủ đề cụ thể, thú vị (ví dụ: 'Đi Siêu Thị', 'Khám Bệnh', 'Đồ Dùng Học Tập', 'Thời Tiết Bốn Mùa', 'Thể Thao & Vận Động', 'Khách Sạn & Du Lịch', 'Phương Hướng & Địa Điểm', 'Cảm Xúc & Tính Cách', 'Nghề Nghiệp & Công Sở', 'Trang Phục & Màu Sắc', 'Động Vật Quanh Ta', 'Nhà Bếp & Nấu Ăn'...).
3. TUYỆT ĐỐI CẤM sử dụng lại bất kỳ từ nào đã từng xuất hiện trên kênh trong danh sách sau:
   [${allUsedWordsStr}]
   (CẤM quanh quẩn các từ quá quen thuộc như: 爸爸, 妈妈, 老师, 学生, 朋友, 苹果, 米饭, 吃, 喝, 看 nếu chúng đã có trong danh sách trên). 100% cả 5 từ trong bộ PHẢI LÀ TỪ MỚI CHƯA CÓ TRONG DANH SÁCH!
4. CÂN ĐỐI CẤP ĐỘ: Ưu tiên chọn lọc từ vựng thuộc HSK 1, HSK 2 và HSK 3 để mở rộng vốn từ phong phú cho người học.
5. Pinyin phải CHUẨN XÁC, có ĐẦY ĐỦ THANH ĐIỆU (ā, á, ǎ, à, ē, é, ě, è, ī, í, ǐ, ì, ō, ó, ǒ, ò, ū, ú, ǔ, ù, ǖ, ǘ, ǚ, ǜ) và BẮT BUỘC MỖI CHỮ HÁN PHẢI CÓ ĐÚNG 1 ÂM TIẾT CÁCH NHAU BẰNG DẤU CÁCH (1-to-1 match). Ví dụ: '公共汽车' -> 'gōng gòng qì chē', '自行车' -> 'zì xíng chē', '出租车' -> 'chū zū chē' (TUYỆT ĐỐI KHÔNG viết dính liền 'gōnggòng qìchē').
6. Nghĩa tiếng Việt ngắn gọn, súc tích, TỐI ĐA 30 KÝ TỰ (tuyệt đối không quá 35 ký tự để không tràn khung video).
7. Toàn bộ chữ Hán BẮT BUỘC là chữ Giản thể (Simplified Chinese).
8. Phản hồi DUY NHẤT một chuỗi JSON hợp lệ không có văn bản giải thích thừa.

CẤU TRÚC JSON MẪU:
[
  {
    "topic": "HSK 2 • Đồ Dùng Công Sở",
    "level": "HSK 2",
    "words": [
      {"hanzi": "电脑", "pinyin": "diàn nǎo", "meaning": "Máy vi tính"},
      {"hanzi": "打印", "pinyin": "dǎ yìn", "meaning": "In ấn"},
      {"hanzi": "会议", "pinyin": "huì yì", "meaning": "Cuộc họp"},
      {"hanzi": "经理", "pinyin": "jīng lǐ", "meaning": "Giám đốc / Quản lý"},
      {"hanzi": "文件", "pinyin": "wén jiàn", "meaning": "Tài liệu / Hồ sơ"}
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
  const cleanModel = rawModel.replace(/^models\//, "");
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${cleanModel}:generateContent?key=${apiKey}`;

  const response = await fetch(url, {
    method: "POST",
    signal: AbortSignal.timeout(4000),
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
    throw new Error(`[Model: ${cleanModel}] (${response.status}): ${errText.substring(0, 150)}`);
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

  throw new Error("Không thể phân tích định dạng JSON từ phản hồi Gemini.");
}

/**
 * 2. Call Agnes AI (apihub.agnes-ai.com / OpenAI-compatible API Gateway)
 */
async function callAgnesAPI(apiKey, baseUrl, requestedModel, systemPrompt, userPrompt) {
  const cleanBase = (baseUrl || "https://apihub.agnes-ai.com/v1").replace(/\/+$/, "");
  const url = `${cleanBase}/chat/completions`;
  const rawModel = (requestedModel || "agnes-2.0-flash").trim();

  const response = await fetch(url, {
    method: "POST",
    signal: AbortSignal.timeout(5000),
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: rawModel,
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
  const choice = data.choices?.[0];
  let rawText = choice?.message?.content;

  if (Array.isArray(rawText)) {
    rawText = rawText.map(item => item.text || item.content || "").join("\n");
  } else if (!rawText && choice?.message?.reasoning_content) {
    rawText = choice.message.reasoning_content;
  }

  const parsed = parseAIResponseJson(rawText);
  if (parsed && parsed.length > 0) {
    return { data: parsed, modelUsed: rawModel };
  }

  throw new Error("Không thể phân tích định dạng JSON từ phản hồi Agnes AI.");
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
 * Gatekeeper #1: Content Uniqueness & Pedagogical Quality Validator
 * Validates AI output BEFORE saving to Google Sheet
 */
export function validateTopicUniquenessAndQuality(topicItem, history = {}) {
  const allUsedWords = new Set(history.allUsedWords || history.recent5Words || []);
  const allTopics = (history.allTopics || []).map(t => t.toLowerCase().trim());

  const errors = [];
  const topicTitle = (topicItem?.topic || "").trim();
  const words = topicItem?.words || [];

  // 1. Topic Title Duplicate Check
  if (topicTitle && allTopics.includes(topicTitle.toLowerCase())) {
    errors.push(`Chủ đề '${topicTitle}' đã tồn tại trên kênh.`);
  }

  // 2. Exactly 5 Words Check
  if (!Array.isArray(words) || words.length !== 5) {
    errors.push(`Số lượng từ vựng không đúng 5 từ (hiện có: ${words.length}).`);
  }

  // 3. Word Uniqueness Check against entire Sheet history & internal duplicates
  const duplicatedWords = [];
  const internalDuplicates = new Set();

  for (const w of words) {
    const hz = (w?.hanzi || "").trim();
    if (!hz) {
      errors.push("Phát hiện từ vựng bị rỗng chữ Hán.");
      continue;
    }
    if (internalDuplicates.has(hz)) {
      errors.push(`Từ '${hz}' bị lặp lại 2 lần trong cùng một video.`);
    }
    internalDuplicates.add(hz);

    if (allUsedWords.has(hz)) {
      duplicatedWords.push(hz);
    }
  }

  if (duplicatedWords.length > 0) {
    errors.push(`Từ vựng [${duplicatedWords.join(", ")}] đã từng xuất hiện trên kênh.`);
  }

  return {
    isValid: errors.length === 0,
    errors: errors,
    duplicatedWords: duplicatedWords
  };
}

/**
 * Multi-Provider Key Rotation & Failover Orchestrator with Built-in Quality Gatekeeper
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
          const candidate = res.data[0];
          const gateCheck = validateTopicUniquenessAndQuality(candidate, vocabHistory);
          if (gateCheck.isValid) {
            resultTopics = [candidate];
            providerUsed = `Google AI Studio (${res.modelUsed} - Key #${i + 1})`;
            anyAiSucceeded = true;
            console.log(`✨ Successfully generated and PASSED Gatekeeper with ${providerUsed}!`);
            break;
          } else {
            console.warn(`🛑 [Gatekeeper Rejected] Google AI Studio output violated uniqueness: ${gateCheck.errors.join("; ")}`);
            diagnostics.gemini.push(`Key #${i + 1} (${keyShort}): Vi phạm Gatekeeper (${gateCheck.errors.join(", ")})`);
          }
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
          const candidate = res.data[0];
          const gateCheck = validateTopicUniquenessAndQuality(candidate, vocabHistory);
          if (gateCheck.isValid) {
            resultTopics = [candidate];
            providerUsed = `Agnes AI (${res.modelUsed} - Key #${i + 1})`;
            anyAiSucceeded = true;
            console.log(`✨ Successfully generated and PASSED Gatekeeper with ${providerUsed}!`);
            break;
          } else {
            console.warn(`🛑 [Gatekeeper Rejected] Agnes AI output violated uniqueness: ${gateCheck.errors.join("; ")}`);
            diagnostics.agnes.push(`Key #${i + 1} (${keyShort}): Vi phạm Gatekeeper (${gateCheck.errors.join(", ")})`);
          }
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
        const candidate = cfRes.data[0];
        const gateCheck = validateTopicUniquenessAndQuality(candidate, vocabHistory);
        if (gateCheck.isValid) {
          resultTopics = [candidate];
          providerUsed = `Cloudflare Workers AI (${cfRes.modelUsed})`;
          anyAiSucceeded = true;
          console.log(`✨ Successfully generated and PASSED Gatekeeper with ${providerUsed}!`);
        } else {
          console.warn(`🛑 [Gatekeeper Rejected] Cloudflare AI output violated uniqueness: ${gateCheck.errors.join("; ")}`);
          diagnostics.cloudflare.push(`CF AI (${cfModel}): Vi phạm Gatekeeper (${gateCheck.errors.join(", ")})`);
        }
      }
    } catch (err) {
      const cleanErr = (err.message || "Unknown error").substring(0, 180);
      diagnostics.cloudflare.push(`CF AI (${cfModel}): ${cleanErr}`);
      console.warn("⚠️ Cloudflare Workers AI failed:", cleanErr);
    }
  }

  // 4. Fallback to Curated Vocab Bank (Filtered against used words)
  if (!resultTopics || resultTopics.length === 0) {
    console.log("ℹ️ Filtering Built-in High Quality Vocab Bank for unique topics...");
    const allUsedWords = new Set(vocabHistory.allUsedWords || []);
    const validBankTopics = BUILTIN_VOCAB_BANK.filter(topicItem => {
      const words = topicItem.words || [];
      const hasDup = words.some(w => allUsedWords.has(w.hanzi));
      return !hasDup;
    });

    const chosenBank = validBankTopics.length > 0 ? validBankTopics : BUILTIN_VOCAB_BANK;
    const shuffledBank = [...chosenBank].sort(() => 0.5 - Math.random());
    resultTopics = shuffledBank.slice(0, count);
    providerUsed = "Fallback VOCAB_BANK (Unique Verified)";
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
  const now = getVietnamTimestamp();

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
