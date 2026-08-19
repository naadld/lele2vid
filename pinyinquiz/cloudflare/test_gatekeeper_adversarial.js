/**
 * Adversarial Test Harness for Gatekeeper 1 (gatekeeper.js)
 * Empirical testing of boundary conditions, edge cases, and failure modes.
 */

import assert from "node:assert";
import {
  checkSimplifiedChinese,
  checkSingleTopic,
  checkVietnameseMeaning,
  checkPinyinSyllables,
  checkPairRepetition,
  auditIdeaDeterministic,
  processGatekeeperIdea,
  isEnglishOrForeignWord
} from "./src/gatekeeper.js";
import { getConfig } from "./src/config.js";

console.log("===============================================================================");
console.log("🔥 RUNNING ADVERSARIAL STRESS TEST SUITE FOR GATEKEEPER 1");
console.log("===============================================================================");

const testResults = {
  passed: 0,
  failed: 0,
  findings: []
};

function runTest(name, fn) {
  try {
    fn();
    console.log(`  ✅ [PASS] ${name}`);
    testResults.passed++;
  } catch (err) {
    console.error(`  ❌ [FAIL] ${name}: ${err.message}`);
    testResults.failed++;
    testResults.findings.push({ test: name, error: err.message });
  }
}

async function runAsyncTest(name, fn) {
  try {
    await fn();
    console.log(`  ✅ [PASS] ${name}`);
    testResults.passed++;
  } catch (err) {
    console.error(`  ❌ [FAIL] ${name}: ${err.message}`);
    testResults.failed++;
    testResults.findings.push({ test: name, error: err.message });
  }
}

// ============================================================================
// SUITE 1: SINGLE TOPIC RULE ADVERSARIAL TESTS
// ============================================================================
console.log("\n--- SUITE 1: Single Topic Rule Adversarial Challenges ---");

runTest("1.1 Reject ampersand '&' in topic (e.g. 'Đồ Ăn & Thức Uống')", () => {
  const cases = [
    "Đồ Ăn & Thức Uống",
    "Gia đình & bạn bè",
    "Trường học&bệnh viện",
    "& Đồ Dùng",
    "Đồ Dùng &"
  ];
  for (const t of cases) {
    const res = checkSingleTopic(t);
    assert.strictEqual(res.passed, false, `Topic '${t}' containing '&' must fail`);
  }
});

runTest("1.2 Reject plus '+' in topic (e.g. 'Trường Học + Bệnh Viện')", () => {
  const cases = [
    "Trường Học + Bệnh Viện",
    "Rau củ + trái cây",
    "Phòng ngủ+Phòng khách",
    "+ Mua Sắm",
    "Du lịch +"
  ];
  for (const t of cases) {
    const res = checkSingleTopic(t);
    assert.strictEqual(res.passed, false, `Topic '${t}' containing '+' must fail`);
  }
});

runTest("1.3 Reject slashes '/' and '\\' in topic", () => {
  const cases = [
    "Thời Tiết / Mùa Màng",
    "Sách / Vở",
    "Con Vật / Thú Cưng",
    "Thời Tiết \\ Khí Hậu"
  ];
  for (const t of cases) {
    const res = checkSingleTopic(t);
    assert.strictEqual(res.passed, false, `Topic '${t}' containing slashes must fail`);
  }
});

runTest("1.4 Reject Vietnamese compound conjunctions ('VÀ', 'và', 'hoặc', 'với', 'kèm', 'cùng')", () => {
  const cases = [
    "Gia Đình VÀ Bạn Bè",
    "đồ ăn và thức uống",
    "Món ăn hoặc Đồ uống",
    "Bố mẹ với con cái",
    "Cơm kèm canh",
    "Thầy giáo cùng học sinh"
  ];
  for (const t of cases) {
    const res = checkSingleTopic(t);
    assert.strictEqual(res.passed, false, `Compound topic '${t}' must fail`);
  }
});

runTest("1.5 Reject English conjunctions ('and', 'And', 'or', 'plus', 'with')", () => {
  const cases = [
    "Food And Drink",
    "đồ ăn and đồ uống",
    "Trái cây OR rau củ",
    "Nhà bếp with phòng khách",
    "Toán học plus vật lý"
  ];
  for (const t of cases) {
    const res = checkSingleTopic(t);
    assert.strictEqual(res.passed, false, `Topic '${t}' with English conjunction must fail`);
  }
});

runTest("1.6 Reject comma-separated compound listings ('Chủ Đề 1, Chủ Đề 2')", () => {
  const cases = [
    "Đồ Ăn, Nước Uống",
    "Gia Đình, Nhà Cửa, Bạn Bè"
  ];
  for (const t of cases) {
    const res = checkSingleTopic(t);
    assert.strictEqual(res.passed, false, `Topic '${t}' with comma compound must fail`);
  }
});

runTest("1.7 Allow legitimate single topics without false positives", () => {
  const validCases = [
    "Đồ Dùng Học Tập",
    "Phương Tiện Giao Thông",
    "Món Ăn Hằng Ngày",
    "HSK 1 • Đồ Dùng Trong Nhà",
    "Cảm Xúc Con Người",
    "Nghề Nghiệp Phổ Biến",
    "Vàng Bạc Đá Quý" // 'Vàng' starts with 'Và' but is not conjunction 'và'
  ];
  for (const t of validCases) {
    const res = checkSingleTopic(t);
    assert.strictEqual(res.passed, true, `Valid single topic '${t}' must pass`);
  }
});

// ============================================================================
// SUITE 2: LANGUAGE PURITY (NO ENGLISH IN VIETNAMESE MEANING)
// ============================================================================
console.log("\n--- SUITE 2: Language Purity Adversarial Challenges ---");

runTest("2.1 Reject English words in parentheses (e.g. 'Quả táo (apple)')", () => {
  const words = [
    { hanzi: "苹果", meaning: "Quả táo (apple)" },
    { hanzi: "桌子", meaning: "Cái bàn (table)" },
    { hanzi: "椅子", meaning: "Chiếc ghế (chair)" },
    { hanzi: "猫", meaning: "Con mèo (cat)" },
    { hanzi: "狗", meaning: "Con chó (dog)" }
  ];
  const res = checkVietnameseMeaning(words);
  assert.strictEqual(res.passed, false, "Meanings with English in brackets must fail");
  assert.strictEqual(res.violations.length, 5, "All 5 words with English in brackets should be flagged");
});

runTest("2.2 Reject direct English words in meaning", () => {
  const words = [
    { hanzi: "书", meaning: "book" },
    { hanzi: "水", meaning: "water" },
    { hanzi: "老师", meaning: "teacher" },
    { hanzi: "学生", meaning: "student" },
    { hanzi: "学校", meaning: "school" }
  ];
  const res = checkVietnameseMeaning(words);
  assert.strictEqual(res.passed, false, "Direct English words must fail");
  assert.strictEqual(res.violations.length, 5);
});

runTest("2.3 Reject English loanwords and transport terms (bus, car, airport, hotel)", () => {
  const words = [
    { hanzi: "公交车", meaning: "Đi chuyến bus" },
    { hanzi: "车", meaning: "Lái car" },
    { hanzi: "机场", meaning: "Đến airport" },
    { hanzi: "饭店", meaning: "Vào hotel" }
  ];
  const res = checkVietnameseMeaning(words);
  assert.strictEqual(res.passed, false, "Meanings with loanwords must fail");
  assert.ok(res.violations.length >= 4, "Loanwords should be flagged");
});

runTest("2.4 Stress test 'taxi' detection in meaning", () => {
  const words = [
    { hanzi: "出租车", meaning: "Xe taxi" }
  ];
  const res = checkVietnameseMeaning(words);
  console.log(`      [EMPIRICAL] 'Xe taxi' audit result: passed=${res.passed}, violations=${JSON.stringify(res.violations)}`);
});

runTest("2.5 Stress test foreign characters (f, j, w, z) and English morphological patterns", () => {
  assert.strictEqual(isEnglishOrForeignWord("wifi"), true, "'wifi' has 'w', 'f'");
  assert.strictEqual(isEnglishOrForeignWord("pizza"), true, "'pizza' has 'z'");
  assert.strictEqual(isEnglishOrForeignWord("shopping"), true, "'shopping' has 'sh', 'ing'");
  assert.strictEqual(isEnglishOrForeignWord("meeting"), true, "'meeting' has 'ing'");
  assert.strictEqual(isEnglishOrForeignWord("laptop"), true, "'laptop' has 'pt'");
});

runTest("2.6 Allow pure Vietnamese meanings without false positives", () => {
  const pureVnWords = [
    { hanzi: "筷子", meaning: "Đôi đũa" },
    { hanzi: "米饭", meaning: "Cơm trắng" },
    { hanzi: "老师", meaning: "Thầy cô giáo" },
    { hanzi: "学校", meaning: "Trường học" },
    { hanzi: "苹果", meaning: "Quả táo đỏ" }
  ];
  const res = checkVietnameseMeaning(pureVnWords);
  assert.strictEqual(res.passed, true, "Pure Vietnamese meanings must pass");
  assert.strictEqual(res.violations.length, 0);
});

// ============================================================================
// SUITE 3: CHARACTER SET (SIMPLIFIED VS TRADITIONAL CHINESE)
// ============================================================================
console.log("\n--- SUITE 3: Character Set Adversarial Challenges ---");

runTest("3.1 Reject common Traditional Chinese characters (國, 車, 說, 學, 這, 門, 經)", () => {
  const traditionalWords = [
    { hanzi: "中國", pinyin: "zhōng guó", meaning: "Trung Quốc" },
    { hanzi: "車站", pinyin: "chē zhàn", meaning: "Bến xe" },
    { hanzi: "說話", pinyin: "shuō huà", meaning: "Nói chuyện" },
    { hanzi: "學習", pinyin: "xué xí", meaning: "Học tập" },
    { hanzi: "這是", pinyin: "zhè shì", meaning: "Đây là" }
  ];
  const res = checkSimplifiedChinese(traditionalWords);
  assert.strictEqual(res.passed, false, "Traditional characters must fail");
  assert.strictEqual(res.violations.length, 5, "All 5 traditional words should be flagged");
});

runTest("3.2 Stress test Traditional '蘋果' and '傳統' against gatekeeper table", () => {
  const testWords = [
    { hanzi: "蘋果", pinyin: "píng guǒ", meaning: "Quả táo" }, // 蘋 (Traditional) vs 苹 (Simplified)
    { hanzi: "傳統", pinyin: "chuán tǒng", meaning: "Truyền thống" } // 傳, 統 (Traditional)
  ];
  const res = checkSimplifiedChinese(testWords);
  console.log(`      [EMPIRICAL] '蘋果' & '傳統' audit result: passed=${res.passed}, violations=${JSON.stringify(res.violations)}`);
});

runTest("3.3 Allow 100% Simplified Chinese characters", () => {
  const simplifiedWords = [
    { hanzi: "中国", pinyin: "zhōng guó", meaning: "Trung Quốc" },
    { hanzi: "车站", pinyin: "chē zhàn", meaning: "Bến xe" },
    { hanzi: "说话", pinyin: "shuō huà", meaning: "Nói chuyện" },
    { hanzi: "学习", pinyin: "xué xí", meaning: "Học tập" },
    { hanzi: "这是", pinyin: "zhè shì", meaning: "Đây là" }
  ];
  const res = checkSimplifiedChinese(simplifiedWords);
  assert.strictEqual(res.passed, true, "Simplified characters must pass");
  assert.strictEqual(res.violations.length, 0);
});

// ============================================================================
// SUITE 4: PINYIN TONE & SYLLABLE COUNT MATCHING
// ============================================================================
console.log("\n--- SUITE 4: Pinyin Tone & Syllable Count Adversarial Challenges ---");

runTest("4.1 Reject Syllable Underflow (Syllables < Hanzi chars)", () => {
  const words = [
    { hanzi: "苹果", pinyin: "píng" },          // 2 chars vs 1 syllable
    { hanzi: "出租车", pinyin: "chū zū" },       // 3 chars vs 2 syllables
    { hanzi: "公共汽车", pinyin: "gōng qì chē" } // 4 chars vs 3 syllables
  ];
  const res = checkPinyinSyllables(words);
  assert.strictEqual(res.passed, false, "Syllable underflow must fail");
  assert.strictEqual(res.violations.length, 3);
});

runTest("4.2 Reject Syllable Overflow (Syllables > Hanzi chars)", () => {
  const words = [
    { hanzi: "水", pinyin: "shuǐ guǒ" },         // 1 char vs 2 syllables
    { hanzi: "老师", pinyin: "lǎo shī hǎo" },    // 2 chars vs 3 syllables
    { hanzi: "中国", pinyin: "zhōng guó rén da" } // 2 chars vs 4 syllables
  ];
  const res = checkPinyinSyllables(words);
  assert.strictEqual(res.passed, false, "Syllable overflow must fail");
  assert.strictEqual(res.violations.length, 3);
});

runTest("4.3 Allow valid 1:1 matching Pinyin with tones and neutral tones", () => {
  const words = [
    { hanzi: "筷子", pinyin: "kuài zi" },     // 2 chars vs 2 syllables (neutral tone on zi)
    { hanzi: "水", pinyin: "shuǐ" },           // 1 char vs 1 syllable
    { hanzi: "出租车", pinyin: "chū zū chē" }, // 3 chars vs 3 syllables
    { hanzi: "绿茶", pinyin: "lǜ chá" },       // ü with tone
    { hanzi: "女", pinyin: "nǚ" }              // ü with 3rd tone
  ];
  const res = checkPinyinSyllables(words);
  assert.strictEqual(res.passed, true, "1:1 matching pinyin must pass");
  assert.strictEqual(res.violations.length, 0);
});

runTest("4.4 Stress test plain ASCII unaccented Pinyin ('ping guo' vs 'píng guǒ')", () => {
  const plainAsciiWords = [
    { hanzi: "苹果", pinyin: "ping guo" },
    { hanzi: "老师", pinyin: "lao shi" }
  ];
  const res = checkPinyinSyllables(plainAsciiWords);
  console.log(`      [EMPIRICAL] Plain ASCII Pinyin audit result: passed=${res.passed}, violations=${JSON.stringify(res.violations)}`);
});

// ============================================================================
// SUITE 5: PAIR REPETITION & HISTORICAL OVERLAP
// ============================================================================
console.log("\n--- SUITE 5: Pair Repetition Adversarial Challenges ---");

runTest("5.1 Reject Intra-batch Duplicates (Identical Hanzi in same batch)", () => {
  const duplicateBatch = [
    { hanzi: "苹果" },
    { hanzi: "苹果" },
    { hanzi: "香蕉" },
    { hanzi: "西瓜" },
    { hanzi: "草莓" }
  ];
  const res = checkPairRepetition(duplicateBatch, []);
  assert.strictEqual(res.passed, false, "Intra-batch duplicate words must fail");
  assert.ok(res.violations[0].includes("Trùng lặp từ vựng trong cùng một bộ"), "Identifies intra-batch duplicate");
});

runTest("5.2 Reject >= 2 shared words with past database batches", () => {
  const pastBatches = [
    { id: "1", topic: "Hoa Quả", words: ["苹果", "香蕉", "西瓜", "葡萄", "草莓"] },
    { id: "2", topic: "Gia Đình", words: ["爸爸", "妈妈", "哥哥", "姐姐", "弟弟"] }
  ];

  // 2 shared words with Batch 1 ("苹果", "香蕉")
  const overlap2 = [
    { hanzi: "苹果" },
    { hanzi: "香蕉" },
    { hanzi: "橘子" },
    { hanzi: "桃子" },
    { hanzi: "梨" }
  ];
  const res2 = checkPairRepetition(overlap2, pastBatches);
  assert.strictEqual(res2.passed, false, "2 shared words with past batch must fail");
  assert.ok(res2.violations[0].includes("Trùng lặp cặp từ (2 từ"), "Identifies 2-word pair overlap");

  // 3 shared words with Batch 2 ("爸爸", "妈妈", "哥哥")
  const overlap3 = [
    { hanzi: "爸爸" },
    { hanzi: "妈妈" },
    { hanzi: "哥哥" },
    { hanzi: "爷爷" },
    { hanzi: "奶奶" }
  ];
  const res3 = checkPairRepetition(overlap3, pastBatches);
  assert.strictEqual(res3.passed, false, "3 shared words with past batch must fail");
  assert.ok(res3.violations[0].includes("Trùng lặp cặp từ (3 từ"), "Identifies 3-word overlap");
});

runTest("5.3 Allow <= 1 shared word with past database batches", () => {
  const pastBatches = [
    { id: "1", topic: "Hoa Quả", words: ["苹果", "香蕉", "西瓜", "葡萄", "草莓"] }
  ];

  // 1 shared word ("苹果") + 4 new words
  const validBatch = [
    { hanzi: "苹果" },
    { hanzi: "橘子" },
    { hanzi: "桃子" },
    { hanzi: "梨" },
    { hanzi: "芒果" }
  ];
  const res = checkPairRepetition(validBatch, pastBatches);
  assert.strictEqual(res.passed, true, "1 shared word with past batch must pass");
  assert.strictEqual(res.violations.length, 0);
});

// ============================================================================
// SUITE 6: RETRY PROTOCOL & STRIKE 3 ROW DELETION
// ============================================================================
console.log("\n--- SUITE 6: Retry Protocol & Strike 3 Deletion Challenges ---");

await runAsyncTest("6.1 Attempt 1 (retry_count: 0) triggers Step 2 re-gen with retry_count=1", async () => {
  const mockEnv = {
    GITHUB_TOKEN: "mock_token",
    GITHUB_REPO_OWNER: "naadld",
    GITHUB_REPO_NAME: "lele2vid",
    GEMINI_API_KEYS: "k1,k2,k3,k4,k5,k6",
    TELEGRAM_BOT_TOKEN: "",
    TELEGRAM_CHAT_ID: "1187577977",
    SPREADSHEET_ID: "mock_sheet",
    SHEET_TAB_NAME: "pinyin"
  };
  const config = getConfig(mockEnv);

  const invalidIdea = {
    row_id: "batch_test_01",
    topic: "Đồ Ăn & Thức Uống", // VIOLATION
    level: "HSK 1",
    words: [
      { hanzi: "水", pinyin: "shuǐ", meaning: "Nước" },
      { hanzi: "米饭", pinyin: "mǐ fàn", meaning: "Cơm" },
      { hanzi: "面", pinyin: "miàn", meaning: "Mì" },
      { hanzi: "肉", pinyin: "ròu", meaning: "Thịt" },
      { hanzi: "菜", pinyin: "cài", meaning: "Rau" }
    ],
    retry_count: 0
  };

  const res = await processGatekeeperIdea(mockEnv, config, invalidIdea);
  assert.strictEqual(res.success, false);
  assert.strictEqual(res.status, "Rejected");
  assert.strictEqual(res.action, "call_step_2");
  assert.strictEqual(res.retry_count, 1);
  assert.ok(res.error_reasons.length > 0);
});

await runAsyncTest("6.2 Attempt 2 (retry_count: 1) triggers Step 2 re-gen with retry_count=2", async () => {
  const mockEnv = {
    GITHUB_TOKEN: "mock_token",
    GITHUB_REPO_OWNER: "naadld",
    GITHUB_REPO_NAME: "lele2vid",
    GEMINI_API_KEYS: "k1,k2,k3,k4,k5,k6",
    TELEGRAM_BOT_TOKEN: "",
    TELEGRAM_CHAT_ID: "1187577977",
    SPREADSHEET_ID: "mock_sheet",
    SHEET_TAB_NAME: "pinyin"
  };
  const config = getConfig(mockEnv);

  const invalidIdea = {
    row_id: "batch_test_02",
    topic: "Gia Đình VÀ Bạn Bè", // VIOLATION
    level: "HSK 1",
    words: [
      { hanzi: "水", pinyin: "shuǐ", meaning: "Nước" },
      { hanzi: "米饭", pinyin: "mǐ fàn", meaning: "Cơm" },
      { hanzi: "面", pinyin: "miàn", meaning: "Mì" },
      { hanzi: "肉", pinyin: "ròu", meaning: "Thịt" },
      { hanzi: "菜", pinyin: "cài", meaning: "Rau" }
    ],
    retry_count: 1
  };

  const res = await processGatekeeperIdea(mockEnv, config, invalidIdea);
  assert.strictEqual(res.success, false);
  assert.strictEqual(res.status, "Rejected");
  assert.strictEqual(res.action, "call_step_2");
  assert.strictEqual(res.retry_count, 2);
});

await runAsyncTest("6.3 Attempt 3 (Strike 3, retry_count: 2) triggers complete row deletion", async () => {
  const mockEnv = {
    GITHUB_TOKEN: "mock_token",
    GITHUB_REPO_OWNER: "naadld",
    GITHUB_REPO_NAME: "lele2vid",
    GEMINI_API_KEYS: "k1,k2,k3,k4,k5,k6",
    TELEGRAM_BOT_TOKEN: "",
    TELEGRAM_CHAT_ID: "1187577977",
    SPREADSHEET_ID: "mock_sheet",
    SHEET_TAB_NAME: "pinyin"
  };
  const config = getConfig(mockEnv);

  const strike3Idea = {
    row_id: "batch_test_03",
    topic: "Thời Tiết / Khí Hậu", // VIOLATION
    level: "HSK 1",
    words: [
      { hanzi: "水", pinyin: "shuǐ", meaning: "Nước" },
      { hanzi: "米饭", pinyin: "mǐ fàn", meaning: "Cơm" },
      { hanzi: "面", pinyin: "miàn", meaning: "Mì" },
      { hanzi: "肉", pinyin: "ròu", meaning: "Thịt" },
      { hanzi: "菜", pinyin: "cài", meaning: "Rau" }
    ],
    retry_count: 2
  };

  const res = await processGatekeeperIdea(mockEnv, config, strike3Idea);
  assert.strictEqual(res.success, false);
  assert.strictEqual(res.status, "Deleted");
  assert.strictEqual(res.action, "delete_row");
  assert.strictEqual(res.retry_count, 3);
  assert.ok(res.message.includes("Strike 3"));
});

console.log("\n===============================================================================");
console.log(`📊 ADVERSARIAL TEST SUMMARY: Total=${testResults.passed + testResults.failed}, Passed=${testResults.passed}, Failed=${testResults.failed}`);
console.log("===============================================================================");

if (testResults.failed > 0) {
  console.log("Failed test details:");
  console.log(JSON.stringify(testResults.findings, null, 2));
}
