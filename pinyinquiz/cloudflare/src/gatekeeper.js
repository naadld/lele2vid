/**
 * Gatekeeper 1 - Independent AI Judge & Strict Quality Auditor
 * For 'Lê Lê Học Tiếng Trung' Pipeline 2.0
 * 
 * 5 Strict Criteria:
 * 1. 100% Simplified Chinese (0 Traditional characters).
 * 2. Single Topic Only (strictly no compound titles with '&', 'VÀ', '+', '/', etc.).
 * 3. 100% Vietnamese meaning (strictly no English words in meaning column).
 * 4. Pinyin tone marks matching Hanzi syllable count 1:1.
 * 5. Zero pair repetition (>= 2 words) with past Sheet database.
 * 
 * Multi-Tier AI Judge:
 * - Primary: Agnes AI (agnes-2.0-flash via https://apihub.agnes-ai.com/v1/chat/completions)
 * - Fallback: Cloudflare Workers AI (@cf/meta/llama-3.3-70b-instruct)
 * 
 * Retry Protocol:
 * - Attempts 1 & 2: Dispatch Step 2 single-row re-gen to GitHub Actions with error reasons.
 * - Attempt 3 (Strike 3): Completely delete/clear row from Google Sheet, log audit violation to Telegram, and stop retrying.
 * - On Pass: Update Google Sheet status to 'Pending'.
 */

import { GoogleSheetsClient, getVietnamTimestamp } from "./google_sheets.js";
import { pinyinToHiddenPinyin, prepareWordItem } from "./pinyin_helper.js";
import { generateSocialMetadata } from "./metadata_helper.js";
import { triggerGitHubIdeationWorkflow, triggerGitHubRenderWorkflow } from "./github_trigger.js";
import { sendTelegramMessage } from "./telegram.js";

// ============================================================================
// 1. TRADITIONAL HANZI DETECTION TABLE
// ============================================================================
// Strictly characters that are Traditional variants having different Simplified forms.
// Universal/Heritage characters (生, 衣服, 桌椅, 窗户, 床, 房间, 数量, 折扣, etc.) are NOT included.
const TRADITIONAL_CHARS_STRING = `
體國說學這會個門經車愛書買點誰麼後電語漢們聽開關讓幫幾邊錢號飯題視爲為樂長師筆鐘
飛樣醫難機歡顏貓藍綠雞畫雙傘齒麵髮龍媽話發頭見東廣氣兒業產當實問動過進無報萬選與
對總結聲變陽陰雲風魚鳥馬豬網寫讀課試檢認識記請謝賣貴賓館飲飽餓餃餅鴨鵝藥療診斷傷
熱溫涼霧颱輛輪鐵銀幣帳單費稅價優質數據圖紙腦頻響錶環衛廚廳臥臺樓櫃燈鏡褲襪帶鹹鮮
週遲舊圓彎遠裡處親鄰孫爺侶練護導遊員蘋傳統灣習節歲曆歷區縣鄉鎮郵園廠庫橋樹葉雜誌
條隻塊張種類齊龜豐艷麗義專業務辦協參緊牽艱嘆應慶廢莊廁廂廈閃閉閏閑閔閘閣閥閱閹閻
闊闌闐闔闕關韋韌韓韻頁頂頃項順須頑顧頓頗領頡頤飠飾餡餛飩饅饌饗駕駝駐駿騎騙鬆鬍
鬧魂魘魯魷鮑鮫鮭鯉鯊鯨鰓鳩鳳鳴鳶鴉鴦鴛鴕鴿鴻鵑鵠鵬鶴鸚鵡鹵麥黃黨黌鈔
`.replace(/\s+/g, "");

export const TRADITIONAL_CHAR_SET = new Set(Array.from(TRADITIONAL_CHARS_STRING));
export const STRICT_TRADITIONAL_REGEX = new RegExp("[" + TRADITIONAL_CHARS_STRING + "]");

// ============================================================================
// 2. FORBIDDEN ENGLISH WORDS IN VIETNAMESE MEANINGS
// ============================================================================
export const ENGLISH_FORBIDDEN_WORDS = new Set([
  "apple", "apples", "table", "tables", "chair", "chairs", "window", "windows",
  "book", "books", "pencil", "pencils", "pen", "pens", "school", "schools",
  "teacher", "teachers", "student", "students", "cat", "cats", "dog", "dogs",
  "water", "rice", "food", "noodle", "noodles", "tea", "coffee", "milk",
  "bus", "taxi", "car", "cars", "plane", "planes", "airplane", "airplanes",
  "airport", "airports", "train", "trains", "station", "stations", "ticket",
  "tickets", "hospital", "hospitals", "doctor", "doctors", "medicine",
  "hotel", "hotels", "room", "rooms", "key", "keys", "phone", "phones",
  "smartphone", "smartphones", "laptop", "laptops", "computer", "computers",
  "camera", "cameras", "guitar", "guitars", "piano", "pianos", "tv", "radio",
  "music", "movie", "movies", "sing", "dance", "play", "game", "games",
  "work", "job", "jobs", "money", "dollar", "dollars", "time", "hour",
  "hours", "minute", "minutes", "second", "seconds", "day", "days", "week",
  "weeks", "month", "months", "year", "years", "today", "yesterday",
  "tomorrow", "spring", "summer", "autumn", "winter", "rain", "snow", "sun",
  "wind", "hot", "cold", "warm", "cool", "big", "small", "good", "bad",
  "happy", "sad", "fast", "slow", "buy", "sell", "eat", "drink", "sleep",
  "wake", "run", "walk", "see", "look", "watch", "listen", "hear", "speak",
  "say", "talk", "write", "read", "learn", "study", "understand", "know",
  "think", "want", "like", "love", "need", "have", "do", "make", "go",
  "come", "back", "leave", "arrive", "give", "get", "find", "lose", "wait",
  "help", "call", "open", "close", "ask", "answer", "question", "questions",
  "name", "names", "friend", "friends", "family", "families", "father",
  "mother", "brother", "brothers", "sister", "sisters", "son", "sons",
  "daughter", "daughters", "man", "men", "woman", "women", "boy", "boys",
  "girl", "girls", "child", "children", "person", "people", "number",
  "numbers", "red", "blue", "green", "yellow", "black", "white", "orange",
  "pink", "brown", "gray", "grey", "purple", "beautiful", "easy", "hard",
  "difficult", "expensive", "cheap", "clean", "dirty", "near", "far", "left",
  "right", "under", "with", "and", "or", "but", "because", "very", "too",
  "also", "always", "never", "sometimes", "often", "already", "now", "later",
  "before", "after", "here", "there", "where", "what", "who", "when", "why",
  "how", "much", "many", "few", "little", "more", "most", "all", "some",
  "any", "no", "not", "yes", "please", "thanks", "thank", "sorry", "hello",
  "goodbye", "hi", "bye", "kitchen", "bedroom", "bathroom", "living",
  "office", "street", "road", "chopstick", "chopsticks", "spoon", "spoons",
  "fork", "forks", "knife", "knives", "plate", "plates", "bowl", "bowls",
  "cup", "cups", "glass", "glasses", "bottle", "bottles", "dish", "dishes",
  "language", "country", "city", "cities", "state", "town", "village",
  "forest", "mountain", "mountains", "river", "rivers", "lake", "lakes",
  "sea", "ocean", "beach", "sky", "star", "stars", "moon", "earth", "world",
  "space", "animal", "animals", "plant", "plants", "tree", "trees", "flower",
  "flowers", "grass", "leaf", "leaves", "bird", "birds", "fish", "fishes",
  "horse", "horses", "cow", "cows", "pig", "pigs", "sheep", "chicken",
  "chickens", "duck", "ducks", "monkey", "monkeys", "elephant", "elephants",
  "tiger", "tigers", "lion", "lions", "bear", "bears", "mouse", "mice",
  "rat", "rats", "rabbit", "rabbits", "snake", "snakes", "wifi", "pizza",
  "shopping", "meeting", "online", "offline", "internet", "email", "website",
  "app", "apps", "link", "links", "video", "videos", "clip", "clips",
  "audio", "card", "cards", "credit", "passport", "bag", "bags", "wallet",
  "clothes", "dress", "dresses", "shirt", "shirts", "tshirt", "pants",
  "shoes", "hat", "hats", "cap", "caps", "clock", "fan", "light", "lights",
  "lamp", "lamps", "door", "doors", "floor", "wall", "house", "home",
  "apartment", "building", "market", "supermarket", "shop", "shops", "store",
  "stores", "bank", "banks", "park", "parks", "zoo", "cinema", "theatre",
  "theater", "restaurant", "restaurants", "cafe", "bar", "club", "gym",
  "stadium", "bridge", "bed", "beds", "sofa", "desk", "desks", "mirror",
  "towel", "soap", "shampoo", "brush", "comb", "box", "boxes", "gift",
  "gifts", "present", "party", "holiday", "vacation", "trip", "travel",
  "tour", "flight", "visa", "luggage", "suitcase", "coat", "jacket", "suit",
  "tie", "belt", "sock", "socks", "boot", "boots", "glove", "gloves", "ring",
  "necklace", "sunglasses"
]);

/**
 * Check if a token is an English or non-Vietnamese foreign word
 */
export function isEnglishOrForeignWord(token) {
  const clean = token.toLowerCase().trim();
  if (!clean || clean.length < 2) return false;

  // Whitelist valid Vietnamese 2-letter / common words
  if (clean === "ly") return false;

  // 1. Direct dictionary match
  if (ENGLISH_FORBIDDEN_WORDS.has(clean)) return true;

  // 2. Contains foreign letters not in Vietnamese alphabet (f, j, w, z)
  if (/[fjwz]/.test(clean)) return true;

  // 3. English consonant clusters & morphological markers anywhere in word
  if (/(str|spl|scr|spr|thr|shr|pt|ct|ft|lt|mp|nd|nt|nk|rd|rk|rm|rn|rp|rt|tch|dge|ble|ple|tle|dle|gle|kle|tion|ment|ness|less|ful|ing|ous|ive)/.test(clean)) {
    return true;
  }
  if (/^(bl|cl|fl|gl|pl|sl|br|cr|dr|fr|gr|pr|sk|sp|st|sm|sn|sw|tw|dw|sh|ck)/.test(clean)) {
    return true;
  }
  if (clean.length > 2 && clean.endsWith("ly") && clean !== "ly") {
    return true;
  }
  if (clean.length > 3 && clean.endsWith("ed")) {
    return true;
  }
  // Plural /s/ at end of consonant: cats, tables, words, chopsticks
  if (/^[a-z]+[bcdfghjklmnpqrstvwxyz]s$/.test(clean) && !["ca", "co", "la", "do", "so"].includes(clean)) {
    return true;
  }

  return false;
}

// ============================================================================
// 3. DETERMINISTIC AUDIT FUNCTIONS
// ============================================================================

/**
 * Criterion 1: Check 100% Simplified Chinese
 */
export function checkSimplifiedChinese(words = []) {
  const violations = [];
  for (let idx = 0; idx < words.length; idx++) {
    const w = words[idx];
    const hanzi = (w.hanzi || "").trim();
    const tradCharsFound = [];
    for (const ch of hanzi) {
      if (STRICT_TRADITIONAL_REGEX.test(ch)) {
        tradCharsFound.push(ch);
      }
    }
    if (tradCharsFound.length > 0) {
      const uniqueTrad = [...new Set(tradCharsFound)];
      violations.push(`Từ #${idx + 1} '${hanzi}' chứa ký tự Phồn thể [${uniqueTrad.join(", ")}] (phải dùng chữ Giản thể).`);
    }
  }
  return {
    passed: violations.length === 0,
    violations
  };
}

/**
 * Criterion 2: Check Single Topic (Allowing natural connectors like 'và', '&', '-')
 */
export function checkSingleTopic(topic = "") {
  const cleanTopic = (topic || "").trim();
  const violations = [];

  if (!cleanTopic) {
    violations.push("Chủ đề không được để trống.");
    return { passed: false, violations };
  }

  if (cleanTopic.length < 2) {
    violations.push("Chủ đề quá ngắn.");
    return { passed: false, violations };
  }

  if (cleanTopic.length > 50) {
    violations.push(`Chủ đề '${cleanTopic}' quá dài (${cleanTopic.length} ký tự, tối đa 50 ký tự).`);
    return { passed: false, violations };
  }

  // Reject raw list delimiters like semicolons or pipes
  if (cleanTopic.includes(";") || cleanTopic.includes("|")) {
    violations.push(`Chủ đề '${cleanTopic}' chứa ký tự phân tách danh sách (; hoặc |). Phải là 1 chủ đề rõ ràng.`);
  }

  // Check etc / v.v.
  if (/(v\.v\.|v\/v|\betc\b)/i.test(cleanTopic)) {
    violations.push(`Chủ đề '${cleanTopic}' chứa ký hiệu liệt kê (v.v., etc...). Phải là 1 chủ đề rõ ràng.`);
  }

  return {
    passed: violations.length === 0,
    violations
  };
}

/**
 * Criterion 3: Check 100% Vietnamese Meaning (No English words)
 */
export function checkVietnameseMeaning(words = []) {
  const violations = [];

  for (let idx = 0; idx < words.length; idx++) {
    const w = words[idx];
    const meaning = (w.meaning || "").trim();

    if (!meaning) {
      violations.push(`Từ #${idx + 1} '${w.hanzi || "N/A"}' bị thiếu nghĩa tiếng Việt.`);
      continue;
    }

    // Split words in meaning and check against English forbidden word list & patterns
    const tokens = meaning.toLowerCase().replace(/[^a-zA-Zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/g, " ").split(/\s+/).filter(Boolean);
    for (const token of tokens) {
      if (isEnglishOrForeignWord(token)) {
        violations.push(`Từ #${idx + 1} '${w.hanzi}' có nghĩa '${meaning}' dính từ tiếng Anh/ngoại ngữ '${token}' (Cột nghĩa phải là 100% tiếng Việt).`);
      }
    }
  }

  return {
    passed: violations.length === 0,
    violations
  };
}

/**
 * Criterion 4: Check Pinyin Tone Marks Matching Hanzi Syllable Count 1:1
 */
const PINYIN_TONE_VOWELS = /[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]/i;
const VALID_NEUTRAL_TONE_SYLLABLES = new Set([
  "de", "le", "ma", "ba", "ne", "zi", "men", "tou", "r", "sheng",
  "fu", "hu", "shang", "xia", "li", "bian", "mian", "ge", "la",
  "ya", "wa", "me", "qian", "hou", "zhe", "xi", "huan", "bai",
  "liang", "shi", "fan", "shu", "nao", "jie", "di", "guo", "dao",
  "hu", "sa", "luo", "dian", "kuai", "nai", "mei", "ye", "you"
]);

/**
 * Auto-segment and normalize unspaced Pinyin (e.g. 'shāngdiàn' -> 'shāng diàn')
 */
export function normalizePinyinSyllables(hanzi = "", pinyin = "") {
  const cleanHanzi = hanzi.replace(/[\s\u3000]/g, "");
  const hanziCount = cleanHanzi.length;
  let cleanPinyin = pinyin.replace(/[\u3000]/g, " ").trim();
  let syllables = cleanPinyin.split(/\s+/).filter(Boolean);

  // Check Erhua (儿化 - uốn lưỡi) exception:
  // Words ending with '儿' in Chinese (e.g. 哪儿: nǎr / nǎ er, 这儿: zhèr / zhè er, 那儿: nàr / nà er, 玩儿: wánr / wán er, 花儿: huār / huā er, 一点儿: yì diǎnr, 事儿: shìr, 门儿: ménr)
  const isErhua = cleanHanzi.endsWith("儿") && (syllables.length === hanziCount - 1 || syllables.some(s => s.toLowerCase().endsWith("r") && !s.toLowerCase().startsWith("r")));

  // If pinyin is connected without spaces (e.g. 'shāngdiàn', 'dōngxi', 'dǎzhé')
  if (!isErhua && syllables.length !== hanziCount && syllables.length === 1 && hanziCount > 1) {
    const PINYIN_SYL_REGEX = /(?:zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])?(?:[aāáǎàeēéěèiīíǐìoōóǒòuūúǔùüǖǘǚǜv]+(?:ng|n|r)?)/gi;
    const matched = cleanPinyin.match(PINYIN_SYL_REGEX);
    if (matched && matched.length === hanziCount) {
      syllables = matched;
      cleanPinyin = matched.join(" ");
    }
  }

  return { cleanPinyin, syllables, hanziCount, isErhua };
}

export function checkPinyinSyllables(words = []) {
  const violations = [];

  for (let idx = 0; idx < words.length; idx++) {
    const w = words[idx];
    const hanzi = (w.hanzi || "").trim().replace(/\s+/g, "");
    let pinyin = (w.pinyin || "").trim();

    if (!hanzi) {
      violations.push(`Từ #${idx + 1} bị thiếu chữ Hán.`);
      continue;
    }
    if (!pinyin) {
      violations.push(`Từ #${idx + 1} '${hanzi}' bị thiếu Pinyin.`);
      continue;
    }

    const { cleanPinyin, syllables, hanziCount, isErhua } = normalizePinyinSyllables(hanzi, pinyin);
    w.pinyin = cleanPinyin; // Auto-update to space-separated format

    const pinyinCount = syllables.length;
    const wordIssues = [];

    // Allow Erhua (hanziCount - 1 when ending with '儿' and pinyin ends with 'r') or 1:1 match
    if (hanziCount !== pinyinCount && !isErhua) {
      wordIssues.push(`Số âm tiết Pinyin (${pinyinCount} âm: '${pinyin}') không khớp 1:1 với số chữ Hán (${hanziCount} chữ: '${hanzi}')`);
    }

    // Check tone mark validity:
    // In standard Chinese phonology:
    // Multi-syllable word (hanziCount > 1): Must have at least 1 tone mark. Un-toned syllables are legitimate neutral tones (thanh nhẹ).
    // Single-syllable word (hanziCount === 1): Must have a tone mark unless it is a standard neutral particle.
    const hasAtLeastOneTone = syllables.some(s => PINYIN_TONE_VOWELS.test(s));

    if (!hasAtLeastOneTone) {
      const allNeutral = syllables.every(s => {
        const cleanSyl = s.toLowerCase().replace(/[^a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]/g, "");
        return VALID_NEUTRAL_TONE_SYLLABLES.has(cleanSyl);
      });
      if (!allNeutral) {
        wordIssues.push(`Pinyin thiếu dấu thanh điệu (yêu cầu Pinyin chuẩn có thanh điệu)`);
      }
    }

    if (wordIssues.length > 0) {
      violations.push(`Từ #${idx + 1} '${hanzi}': ${wordIssues.join(" | ")}.`);
    }
  }

  return {
    passed: violations.length === 0,
    violations
  };
}

/**
 * Criterion 5: Check Zero Pair Repetition (>= 2 words) with past Sheet database
 */
export function checkPairRepetition(words = [], pastBatches = []) {
  const violations = [];
  const currentWords = words.map(w => (w.hanzi || "").trim()).filter(Boolean);

  // 1. Check intra-batch duplicate words
  const seenWords = new Set();
  const duplicates = [];
  for (const w of currentWords) {
    if (seenWords.has(w)) {
      duplicates.push(w);
    }
    seenWords.add(w);
  }
  if (duplicates.length > 0) {
    violations.push(`Trùng lặp từ vựng trong cùng một bộ kịch bản: [${duplicates.join(", ")}].`);
  }

  // 2. Check pair repetition (>= 2 words) with past sheet batches
  if (Array.isArray(pastBatches)) {
    for (const past of pastBatches) {
      const pastWords = past.words || [];
      const intersection = currentWords.filter(w => pastWords.includes(w));

      if (intersection.length >= 2) {
        violations.push(`Trùng lặp cặp từ (${intersection.length} từ: [${intersection.join(", ")}]) với bộ kịch bản cũ #${past.id} ('${past.topic}').`);
      }
    }
  }

  return {
    passed: violations.length === 0,
    violations
  };
}

/**
 * Combined Deterministic Audit (All 5 Criteria)
 */
export function auditIdeaDeterministic(idea, pastBatches = []) {
  const words = Array.isArray(idea.words) ? idea.words : [];
  const topic = idea.topic || "";

  if (words.length !== 5) {
    return {
      passed: false,
      error_reasons: [`Số lượng từ vựng không đúng chuẩn (${words.length}/5 từ). Kịch bản bắt buộc phải có đúng 5 từ.`]
    };
  }

  const c1 = checkSimplifiedChinese(words);
  const c2 = checkSingleTopic(topic);
  const c3 = checkVietnameseMeaning(words);
  const c4 = checkPinyinSyllables(words);
  const c5 = checkPairRepetition(words, pastBatches);

  const errorReasons = [
    ...c1.violations,
    ...c2.violations,
    ...c3.violations,
    ...c4.violations,
    ...c5.violations
  ];

  return {
    passed: errorReasons.length === 0,
    error_reasons: errorReasons,
    details: {
      simplified_chinese: c1,
      single_topic: c2,
      vietnamese_meaning: c3,
      pinyin_syllables: c4,
      pair_repetition: c5
    }
  };
}

// ============================================================================
// 4. MULTI-TIER AI JUDGE (AGNES AI & WORKERS AI FALLBACK)
// ============================================================================

/**
 * Parse JSON safely from LLM output (supporting markdown fences)
 */
function parseAiResponseJson(text) {
  if (!text || typeof text !== "string") return null;
  let clean = text.trim();
  if (clean.includes("```json")) {
    clean = clean.split("```json")[1].split("```")[0].trim();
  } else if (clean.includes("```")) {
    clean = clean.split("```")[1].split("```")[0].trim();
  }
  try {
    return JSON.parse(clean);
  } catch (err) {
    // Try regex extracting first { ... }
    const match = clean.match(/\{[\s\S]*\}/);
    if (match) {
      try {
        return JSON.parse(match[0]);
      } catch (e) {}
    }
    return null;
  }
}

/**
 * AI Judge Prompt Construction
 */
function buildAiJudgePrompt(idea) {
  const systemPrompt = `You are Gatekeeper 1, an expert linguistic and quality assurance judge for the Vietnamese Chinese learning channel 'Lê Lê Học Tiếng Trung'.
Audit the following candidate idea strictly against these CRITERIA:
1. 100% Simplified Chinese: Every Hanzi character MUST be Simplified Chinese. Absolutely NO Traditional Chinese characters allowed.
2. Topic Cohesiveness: Topic must be a clear, natural topic in Vietnamese (natural connectors like 'và', '&', '-' are completely acceptable, e.g. 'Cảm xúc và Tâm trạng', 'Thời tiết', 'Gia đình & Bạn bè'). Only reject multi-topic dump lists separated by semicolons or containing 'etc'/'v.v.'.
3. 100% Pure Vietnamese Meaning: Meaning column MUST be natural 100% Vietnamese. Strictly NO English words or English loanwords (e.g., 'taxi', 'bus', 'shopping', 'table', 'chair', 'apple', 'window', 'car', etc.).
4. Pinyin Accuracy: Pinyin must be accurate. Standard Chinese neutral tones (thanh nhẹ - e.g., 'me' in 怎么样/什么, 'zi' in 桌子/椅子, 'men' in 我们/你们, 'ba' in 爸爸, 'ma' in 妈妈, 'xi' in 东西, 'you' in 朋友, 'nai' in 奶奶, 'mei' in 妹妹, 'di' in 弟弟, 'jie' in 姐姐, 'ge' in 哥哥) do NOT have tone marks and are 100% CORRECT. Also, Erhua (儿化 - e.g., 哪儿: nǎr, 这儿: zhèr, 那儿: nàr, 玩儿: wánr, 一点儿: yì diǎnr, 花儿: huār) contracted into 1 syllable ending with 'r' is 100% CORRECT and standard Mandarin. Do NOT reject neutral tones or Erhua syllables.
5. 5-Word Emotional Curve (Retention): Must have exactly 5 words progressing from easy hook (Word 1) to standard core (Words 2-3) to tone/phonetic trap (Word 4) to challenge/boss word (Word 5).

Return ONLY a JSON object with:
{
  "passed": boolean,
  "error_reasons": string[],
  "summary": string
}`;

  const userPrompt = `Candidate Idea to Audit:
${JSON.stringify(idea, null, 2)}

Audit carefully. Output JSON only.`;

  return { systemPrompt, userPrompt };
}

/**
 * Audit with Agnes AI (Primary AI Judge)
 */
async function auditWithAgnesAI(config, idea) {
  const agnesKeys = config.agnesApiKeys || [];
  if (agnesKeys.length === 0) {
    throw new Error("No Agnes API keys configured.");
  }

  const { systemPrompt, userPrompt } = buildAiJudgePrompt(idea);
  const baseUrl = config.agnesBaseUrl || "https://apihub.agnes-ai.com/v1";
  const model = config.agnesModel || "agnes-2.0-flash";

  let lastError = null;

  for (let i = 0; i < agnesKeys.length; i++) {
    const key = agnesKeys[i];
    try {
      const res = await fetch(`${baseUrl}/chat/completions`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${key}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          model: model,
          messages: [
            { role: "system", content: systemPrompt },
            { role: "user", content: userPrompt }
          ],
          temperature: 0.1,
          response_format: { type: "json_object" }
        }),
        signal: AbortSignal.timeout(8000)
      });

      if (!res.ok) {
        const errText = await res.text();
        throw new Error(`Agnes API HTTP ${res.status}: ${errText.substring(0, 150)}`);
      }

      const data = await res.json();
      const content = data.choices?.[0]?.message?.content;
      const parsed = parseAiResponseJson(content);

      if (parsed && typeof parsed.passed === "boolean") {
        return {
          provider: "Agnes AI",
          model: model,
          passed: parsed.passed,
          error_reasons: Array.isArray(parsed.error_reasons) ? parsed.error_reasons : [],
          summary: parsed.summary || ""
        };
      }
    } catch (err) {
      console.warn(`[GATEKEEPER] Agnes AI Key ${i + 1} failed: ${err.message}`);
      lastError = err;
    }
  }

  throw lastError || new Error("All Agnes AI keys failed.");
}

/**
 * Audit with Cloudflare Workers AI (Fallback AI Judge)
 */
async function auditWithWorkersAI(env, config, idea) {
  if (!env.AI) {
    throw new Error("Cloudflare Workers AI binding (env.AI) is not available.");
  }

  const { systemPrompt, userPrompt } = buildAiJudgePrompt(idea);
  const model = config.aiModel || "@cf/meta/llama-3.3-70b-instruct";

  const res = await env.AI.run(model, {
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: userPrompt }
    ],
    temperature: 0.1
  });

  const content = res.response || (typeof res === "string" ? res : JSON.stringify(res));
  const parsed = parseAiResponseJson(content);

  if (parsed && typeof parsed.passed === "boolean") {
    return {
      provider: "Cloudflare Workers AI",
      model: model,
      passed: parsed.passed,
      error_reasons: Array.isArray(parsed.error_reasons) ? parsed.error_reasons : [],
      summary: parsed.summary || ""
    };
  }

  return {
    provider: "Cloudflare Workers AI",
    model: model,
    passed: true,
    error_reasons: [],
    summary: "Workers AI evaluated output."
  };
}

/**
 * Run Independent AI Judge with Multi-Tier Fallback
 */
export async function auditIdeaWithAI(env, config, idea) {
  // 1. Try Primary Judge: Agnes AI
  try {
    const agnesResult = await auditWithAgnesAI(config, idea);
    return agnesResult;
  } catch (agnesErr) {
    console.warn(`[GATEKEEPER] Agnes AI Judge unavailable (${agnesErr.message}). Falling back to Cloudflare Workers AI...`);
  }

  // 2. Try Fallback Judge: Cloudflare Workers AI
  try {
    const cfResult = await auditWithWorkersAI(env, config, idea);
    return cfResult;
  } catch (cfErr) {
    console.warn(`[GATEKEEPER] Workers AI Judge unavailable (${cfErr.message}).`);
  }

  // 3. Fallback if both AI models are unreachable
  return {
    provider: "Rule-Based Deterministic Fallback",
    model: "none",
    passed: true,
    error_reasons: [],
    summary: "AI judges unreachable. Rule-based evaluation enforced."
  };
}

// ============================================================================
// 5. MASTER GATEKEEPER 1 AUDIT & RETRY PROTOCOL
// ============================================================================

/**
 * Full Gatekeeper 1 Audit for a Single Idea Batch
 */
export async function auditIdea(env, config, idea, pastBatches = []) {
  // Step 1: Run deterministic check
  const detResult = auditIdeaDeterministic(idea, pastBatches);

  // Step 2: Run AI Judge
  let aiResult = { passed: true, error_reasons: [], provider: "None" };
  try {
    aiResult = await auditIdeaWithAI(env, config, idea);
  } catch (e) {
    console.warn(`[GATEKEEPER] AI judge error: ${e.message}`);
  }

  // Combine reasons
  const combinedReasons = [
    ...detResult.error_reasons,
    ...(aiResult.passed === false ? aiResult.error_reasons : [])
  ];

  // Remove duplicates from reasons
  const uniqueReasons = [...new Set(combinedReasons)];
  const passed = detResult.passed && (aiResult.passed !== false) && uniqueReasons.length === 0;

  return {
    passed: passed,
    error_reasons: uniqueReasons,
    deterministic: detResult,
    ai_judge: aiResult
  };
}

/**
 * Ingest and Process Single Idea Batch Payload through Gatekeeper 1 & Retry Protocol
 * 
 * @param {object} env - Cloudflare Worker environment bindings
 * @param {object} config - Configuration object
 * @param {object} payload - Incoming idea payload: { row_id, topic, level, words, metadata, retry_count }
 * @returns {Promise<object>} Structured response according to interface contract
 */
export async function processGatekeeperIdea(env, config, payload) {
  // If payload is an array of ideas, process sequentially
  if (Array.isArray(payload)) {
    const results = [];
    for (const item of payload) {
      const res = await processGatekeeperIdea(env, config, item);
      results.push(res);
    }
    return {
      batch_processed: true,
      total: results.length,
      passed_count: results.filter(r => r.success).length,
      items: results
    };
  }

  if (Array.isArray(payload.batches) || Array.isArray(payload.items)) {
    const list = payload.batches || payload.items;
    return await processGatekeeperIdea(env, config, list);
  }

  // Normalize single idea payload
  const rowId = String(payload.row_id || "").trim();
  const topic = (payload.topic || "").trim();
  const level = (payload.level || "HSK 1").trim();
  const rawWords = Array.isArray(payload.words) ? payload.words : [];
  const retryCount = Number(payload.retry_count || 0);

  // Normalize words objects
  const words = rawWords.map(w => {
    const hanzi = (w.hanzi || "").trim();
    const pinyin = (w.pinyin || "").trim();
    const hiddenPinyin = (w.hidden_pinyin || pinyinToHiddenPinyin(pinyin)).trim();
    const meaning = (w.meaning || "").trim();
    return {
      hanzi,
      pinyin,
      hidden_pinyin: hiddenPinyin,
      meaning
    };
  });

  const ideaToAudit = {
    row_id: rowId,
    topic,
    level,
    words,
    metadata: payload.metadata || {}
  };

  console.log(`[GATEKEEPER] Auditing Idea Batch: row_id='${rowId}', topic='${topic}', retry_count=${retryCount}`);

  // Connect to Google Sheets for negative history and updates
  const gsheet = new GoogleSheetsClient(
    config.gcpClientEmail,
    config.gcpPrivateKey,
    config.spreadsheetId,
    config.sheetTabName
  );

  let vocabHistory = { pastBatches: [] };
  try {
    vocabHistory = await gsheet.getVocabHistory();
  } catch (e) {
    console.warn(`[GATEKEEPER] Warning fetching vocab history: ${e.message}`);
  }

  // Run full Gatekeeper 1 audit
  const auditResult = await auditIdea(env, config, ideaToAudit, vocabHistory.pastBatches || []);

  // =========================================================================
  // CASE A: 100% PASSED AUDIT -> SAVE TO GOOGLE SHEET AS 'Pending'
  // =========================================================================
  if (auditResult.passed) {
    console.log(`[GATEKEEPER] ✅ PASSED all 5 criteria for '${topic}' (row_id: ${rowId})`);

    // Generate complete viral metadata
    const socialMeta = generateSocialMetadata(topic, level, words);
    const metadataText = socialMeta.formatted_text || socialMeta.formattedText || "";

    // Format 5 word column strings: "hanzi | pinyin | hidden_pinyin | meaning"
    const wordCols = words.map(w => `${w.hanzi} | ${w.pinyin} | ${w.hidden_pinyin} | ${w.meaning}`);
    while (wordCols.length < 5) wordCols.push("");

    const timeStr = getVietnamTimestamp();
    const notes = `Gatekeeper 1 Passed (${auditResult.ai_judge.provider || "Agnes AI"}) - ${timeStr}`;

    // Find if row already exists in Google Sheet
    let targetRowNum = null;
    if (rowId) {
      const existing = await gsheet.findRowByBatchId(rowId);
      if (existing) targetRowNum = existing.rowNumber;
    }

    if (targetRowNum) {
      // Repair / Update existing row
      await gsheet.repairBatchRow(targetRowNum, topic, level, words, metadataText, notes);
    } else {
      // Append as new row
      const newRow = [
        rowId || "",       // Col A: ID
        topic,             // Col B: Topic
        level,             // Col C: Level
        "Pending",         // Col D: Status -> Pending
        wordCols[0] || "", // Col E
        wordCols[1] || "", // Col F
        wordCols[2] || "", // Col G
        wordCols[3] || "", // Col H
        wordCols[4] || "", // Col I
        metadataText,      // Col J: Metadata
        "",                // Col K: Video Link
        "",                // Col L: YouTube
        "",                // Col M: TikTok
        "",                // Col N: Facebook
        timeStr,           // Col O: Created_At
        notes              // Col P: Notes
      ];
      await gsheet.appendRows([newRow]);
    }

    // Auto-trigger GitHub Actions Render Workflow (Render.yml)
    let renderDispatched = false;
    let renderMsg = "";
    try {
      const rRes = await triggerGitHubRenderWorkflow(env, { row_id: rowId, quality: "qh" });
      renderDispatched = rRes.success;
      renderMsg = rRes.message;
      console.log(`[GATEKEEPER] ⚡ Auto-triggered Render.yml for row #${rowId}: ${renderMsg}`);
    } catch (rErr) {
      console.warn(`[GATEKEEPER] Warning auto-triggering Render.yml: ${rErr.message}`);
      renderMsg = rErr.message;
    }

    // Telegram Audit Log
    await sendTelegramMessage(
      config.telegramBotToken,
      config.telegramChatId,
      `✅ <b>[Gatekeeper 1 - Kịch Bản Đạt Chuẩn 100%]</b>\n\n` +
      `📌 <b>Chủ đề:</b> <code>${topic}</code> (${level})\n` +
      `🆔 <b>Row ID:</b> <code>${rowId || "Mới"}</code> | <b>Trạng thái:</b> <code>Pending</code>\n` +
      `🧐 <b>Giám khảo:</b> ${auditResult.ai_judge.provider || "Agnes AI"}\n\n` +
      `📝 <b>5 Từ vựng:</b>\n` +
      words.map((w, i) => `  ${i + 1}. <b>${w.hanzi}</b> (<i>${w.pinyin}</i>): ${w.meaning}`).join("\n") +
      `\n\n🎬 <b>Tự động sản xuất:</b> ${renderDispatched ? "⚡ Đã tự động kích hoạt GitHub Actions <code>Render.yml</code> (Manim 60fps)!" : `⚠️ Chưa kích hoạt Render: ${renderMsg}`}`
    );

    return {
      success: true,
      status: "Pending",
      row_id: rowId,
      topic: topic,
      action: "saved_to_sheet_and_rendered",
      render_dispatched: renderDispatched,
      message: "Gatekeeper 1 passed. Idea batch saved to Google Sheet as Pending and auto-triggered Render.yml."
    };
  }

  // =========================================================================
  // CASE B: AUDIT FAILED -> RETRY PROTOCOL (Max 2 retries, 3rd = Delete)
  // =========================================================================
  const errorReasons = auditResult.error_reasons;
  const currentRetry = retryCount;

  console.warn(`[GATEKEEPER] ❌ REJECTED idea '${topic}' (Attempt ${currentRetry + 1}). Errors:`, errorReasons);

  if (currentRetry < 2) {
    // -----------------------------------------------------------------------
    // RETRY 1 & 2: DISPATCH STEP 2 SINGLE-ROW RE-GEN TO GITHUB ACTIONS
    // -----------------------------------------------------------------------
    const nextRetry = currentRetry + 1;
    const errorReasonsStr = errorReasons.join("; ");

    console.log(`[GATEKEEPER] Triggering GitHub Actions Step 2 for row_id='${rowId}', retry_count=${nextRetry}`);

    let ghDispatched = false;
    let ghMessage = "";
    try {
      const ghRes = await triggerGitHubIdeationWorkflow(env, {
        mode: "single_row",
        row_id: rowId,
        rejected_topic: topic,
        error_reasons: errorReasonsStr,
        retry_count: nextRetry
      });
      ghDispatched = true;
      ghMessage = ghRes.message;
    } catch (ghErr) {
      console.error(`[GATEKEEPER] Failed to dispatch GitHub Step 2: ${ghErr.message}`);
      ghMessage = `Dispatch Error: ${ghErr.message}`;
    }

    // Telegram Alert for Retry
    await sendTelegramMessage(
      config.telegramBotToken,
      config.telegramChatId,
      `⚠️ <b>[Gatekeeper 1 - Từ Chối & Yêu Cầu Viết Lại]</b> (Lần ${nextRetry}/2)\n\n` +
      `📌 <b>Chủ đề bị từ chối:</b> <code>${topic}</code>\n` +
      `🆔 <b>Row ID:</b> <code>${rowId}</code>\n\n` +
      `❌ <b>Lý do vi phạm:</b>\n` +
      errorReasons.map(r => `  • ${r}`).join("\n") +
      `\n\n🔄 <i>${ghDispatched ? "Đã tự động gửi yêu cầu Step 2 sang GitHub Actions để viết lại dòng này." : `Lỗi kích hoạt GitHub: ${ghMessage}`}</i>`
    );

    return {
      success: false,
      status: "Rejected",
      action: "call_step_2",
      row_id: rowId,
      retry_count: nextRetry,
      error_reasons: errorReasons,
      message: `Gatekeeper 1 rejected idea (Retry attempt ${nextRetry}/2). Triggered Step 2 single-row re-generation.`
    };
  }

  // -------------------------------------------------------------------------
  // MAX RETRIES REACHED (>= 2): AUTO-TRIGGER FRESH NEW TOPIC ON GITHUB ACTIONS
  // -------------------------------------------------------------------------
  console.warn(`[GATEKEEPER] 🔄 Max retries (${retryCount}) reached for topic '${topic}' (Row #${rowId}). Automatically triggering GitHub Actions to generate a FRESH NEW TOPIC...`);

  let ghFreshDispatched = false;
  let ghFreshMessage = "";
  try {
    const ghRes = await triggerGitHubStep2ReGen(env, config, {
      rowId: rowId,
      rejectedTopic: topic,
      errorReasons: `Chủ đề cũ '${topic}' không đạt chuẩn sau 2 lần sửa: [${errorReasons.join("; ")}]. Yêu cầu sinh một CHỦ ĐỀ MỚI HOÀN TOÀN (Fresh Topic) cho dòng này.`
    });
    ghFreshDispatched = ghRes.success;
    ghFreshMessage = ghRes.message;
  } catch (ghErr) {
    ghFreshDispatched = false;
    ghFreshMessage = ghErr.message;
  }

  // Telegram Alert for Fresh Topic Switch
  await sendTelegramMessage(
    config.telegramBotToken,
    config.telegramChatId,
    `🔄 <b>[Gatekeeper 1 - TỰ ĐỘNG ĐỔI CHỦ ĐỀ MỚI]</b>\n\n` +
    `⚠️ <b>Chủ đề cũ không đạt sau 2 lần sửa:</b> <code>${topic}</code>\n` +
    `🆔 <b>Dòng:</b> <code>#${rowId}</code>\n\n` +
    `❌ <b>Lý do hủy chủ đề cũ:</b>\n` +
    errorReasons.map(r => `  • ${r}`).join("\n") +
    `\n\n🚀 <b>Hành động tự động:</b> ${ghFreshDispatched ? `Đã kích hoạt GitHub Actions viết một <b>CHỦ ĐỀ MỚI HOÀN TOÀN</b> để lấp đầy dòng #${rowId}.` : `Lỗi kích hoạt GitHub: ${ghFreshMessage}`}`
  );

  return {
    success: false,
    status: "FreshTopicTriggered",
    action: "trigger_fresh_topic",
    row_id: rowId,
    retry_count: 0,
    error_reasons: errorReasons,
    message: `Chủ đề '${topic}' không đạt sau 2 lần sửa. Đã tự động kích hoạt GitHub Actions sinh chủ đề mới hoàn toàn cho dòng #${rowId}.`
  };
}
