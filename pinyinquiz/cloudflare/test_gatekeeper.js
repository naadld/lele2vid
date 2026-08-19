/**
 * Automated Unit & Integration Tests for Gatekeeper 1 & Control Plane (Milestone 2 Remediation)
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

console.log("===============================================================");
console.log("🧪 RUNNING GATEKEEPER 1 & CONTROL PLANE TESTS (REMEDIATION)");
console.log("===============================================================");

// 1. Criterion 1: Simplified Chinese vs Traditional Chinese
console.log("\n[TEST 1] Simplified vs Traditional Chinese Check");
{
  // 1a. Everyday standard Simplified Chinese (Must NOT produce false positives)
  const validSimplified = [
    { hanzi: "学生", pinyin: "xué sheng", meaning: "Học sinh" },
    { hanzi: "医生", pinyin: "yī shēng", meaning: "Bác sĩ" },
    { hanzi: "衣服", pinyin: "yī fu", meaning: "Quần áo" },
    { hanzi: "桌子", pinyin: "zhuō zi", meaning: "Cái bàn" },
    { hanzi: "椅子", pinyin: "yǐ zi", meaning: "Cái ghế" },
    { hanzi: "医院", pinyin: "yī yuàn", meaning: "Bệnh viện" },
    { hanzi: "火车站", pinyin: "huǒ chē zhàn", meaning: "Ga xe lửa" },
    { hanzi: "面包", pinyin: "miàn bāo", meaning: "Bánh mì" },
    { hanzi: "苹果", pinyin: "píng guǒ", meaning: "Quả táo" },
    { hanzi: "传统", pinyin: "chuán tǒng", meaning: "Truyền thống" }
  ];
  const res1 = checkSimplifiedChinese(validSimplified);
  assert.strictEqual(res1.passed, true, "Standard Simplified Chinese vocabulary must pass");
  assert.strictEqual(res1.violations.length, 0, "No false positives on standard simplified words");
  console.log("  ✅ Passed: Zero false positives on standard Simplified Chinese vocabulary");

  // 1b. Traditional Chinese words (Must strictly fail)
  const traditionalWords = [
    { hanzi: "國語", pinyin: "guó yǔ", meaning: "Quốc ngữ" },     // 國, 語 is traditional
    { hanzi: "車子", pinyin: "chē zi", meaning: "Xe" },          // 車 is traditional
    { hanzi: "蘋果", pinyin: "píng guǒ", meaning: "Quả táo" },    // 蘋 is traditional
    { hanzi: "傳統", pinyin: "chuán tǒng", meaning: "Truyền thống" }, // 傳, 統 is traditional
    { hanzi: "電腦", pinyin: "diàn nǎo", meaning: "Máy vi tính" },  // 電, 腦 is traditional
    { hanzi: "飛機", pinyin: "fēi jī", meaning: "Máy bay" }       // 飛, 機 is traditional
  ];
  const res2 = checkSimplifiedChinese(traditionalWords);
  assert.strictEqual(res2.passed, false, "Traditional Chinese words must fail");
  assert.strictEqual(res2.violations.length, 6, "All 6 traditional words flagged");
  console.log("  ✅ Passed: Correctly detected and rejected traditional characters (國, 車, 蘋, 傳, 統, 電, 腦, 飛, 機)");
}

// 2. Criterion 2: Single Topic Only
console.log("\n[TEST 2] Single Topic Only Check");
{
  const validTopics = [
    "Đồ Dùng Học Tập",
    "Món Ăn Hàng Ngày",
    "Phương Tiện Giao Thông",
    "HSK 1 • Gia Đình",
    "Cảm Xúc Con Người",
    "Nghề Nghiệp Phổ Biến",
    "Vàng Bạc Đá Quý"
  ];
  for (const t of validTopics) {
    const res = checkSingleTopic(t);
    assert.strictEqual(res.passed, true, `Topic '${t}' should pass`);
  }

  const compoundTopics = [
    "Đồ Ăn & Thức Uống",
    "Gia Đình VÀ Bạn Bè",
    "Trường Học + Bệnh Viện",
    "Thời Tiết / Mùa Màng",
    "Food And Drink",
    "Chủ Đề 1, Chủ Đề 2",
    "Món ăn hoặc Đồ uống",
    "Bố mẹ với con cái",
    "Cơm kèm canh",
    "Thầy giáo cùng học sinh"
  ];
  for (const t of compoundTopics) {
    const res = checkSingleTopic(t);
    assert.strictEqual(res.passed, false, `Compound topic '${t}' must fail`);
  }
  console.log("  ✅ Passed: Rejected compound topics containing '&', '+', '/', 'VÀ', 'hoặc', 'với', 'kèm', 'cùng', 'and', ','");
}

// 3. Criterion 3: 100% Vietnamese Meaning (No English Words & Whitelist 'ly')
console.log("\n[TEST 3] Vietnamese Meaning (No English Words & Whitelist 'ly')");
{
  // 3a. Valid pure Vietnamese meanings including 'ly' (ly nước, cái ly)
  const validMeanings = [
    { hanzi: "筷子", meaning: "Đôi đũa" },
    { hanzi: "桌子", meaning: "Cái bàn" },
    { hanzi: "杯子", meaning: "Cái ly" },
    { hanzi: "水", meaning: "Ly nước" },
    { hanzi: "学校", meaning: "Trường học" }
  ];
  const res1 = checkVietnameseMeaning(validMeanings);
  assert.strictEqual(res1.passed, true, "Pure Vietnamese meaning (including 'ly') should pass");
  assert.strictEqual(res1.violations.length, 0);

  // 3b. English word detection & loanwords
  const englishMeanings = [
    { hanzi: "筷子", meaning: "Chopsticks" },
    { hanzi: "桌子", meaning: "Cái table" },
    { hanzi: "椅子", meaning: "Chiếc chair" },
    { hanzi: "猫", meaning: "Con cat màu đen" },
    { hanzi: "狗", meaning: "Con dog" },
    { hanzi: "出租车", meaning: "Xe taxi" },
    { hanzi: "咖啡", meaning: "Uống coffee" },
    { hanzi: "牛奶", meaning: "Hộp milk" },
    { hanzi: "笔记本", meaning: "Chiếc laptop" },
    { hanzi: "手机", meaning: "Cái phone" }
  ];
  const res2 = checkVietnameseMeaning(englishMeanings);
  assert.strictEqual(res2.passed, false, "Meanings containing English must fail");
  assert.strictEqual(res2.violations.length, 10, "All 10 english meanings flagged");
  console.log("  ✅ Passed: Rejected English words (table, chair, dog, cat, taxi, coffee, milk, laptop, phone, chopsticks) while whitelisting 'ly'");
}

// 4. Criterion 4: Pinyin Tone Marks & 1:1 Syllable Matching
console.log("\n[TEST 4] Pinyin Tone Marks & Syllable 1:1 Matching");
{
  // 4a. Valid 1:1 matching Pinyin with tones and valid neutral tones
  const validWords = [
    { hanzi: "苹果", pinyin: "píng guǒ" },    // 2 chars, 2 syllables with tones
    { hanzi: "水", pinyin: "shuǐ" },          // 1 char, 1 syllable with tone
    { hanzi: "出租车", pinyin: "chū zū chē" }, // 3 chars, 3 syllables with tones
    { hanzi: "筷子", pinyin: "kuài zi" },     // neutral tone 'zi'
    { hanzi: "衣服", pinyin: "yī fu" }        // neutral tone 'fu'
  ];
  const res1 = checkPinyinSyllables(validWords);
  assert.strictEqual(res1.passed, true, "1:1 matching pinyin with tone marks should pass");
  assert.strictEqual(res1.violations.length, 0);

  // 4b. Mismatched syllable count
  const mismatchWords = [
    { hanzi: "苹果", pinyin: "píng" },             // 2 chars vs 1 syllable
    { hanzi: "老师", pinyin: "lǎo shī hǎo" },      // 2 chars vs 3 syllables
    { hanzi: "水", pinyin: "" }                    // Missing pinyin
  ];
  const res2 = checkPinyinSyllables(mismatchWords);
  assert.strictEqual(res2.passed, false, "Mismatched syllable count must fail");
  assert.strictEqual(res2.violations.length, 3, "All 3 mismatches flagged");

  // 4c. Plain ASCII unaccented Pinyin (Lacking tone marks)
  const plainAsciiWords = [
    { hanzi: "苹果", pinyin: "ping guo" },
    { hanzi: "老师", pinyin: "lao shi" }
  ];
  const res3 = checkPinyinSyllables(plainAsciiWords);
  assert.strictEqual(res3.passed, false, "Plain ASCII unaccented Pinyin must fail");
  assert.strictEqual(res3.violations.length, 2, "Both plain ASCII words flagged for lacking tones");
  console.log("  ✅ Passed: Enforced Pinyin tone marks (rejected plain ASCII 'ping guo' & 'lao shi') and validated syllable counts");
}

// 5. Criterion 5: Zero Pair Repetition
console.log("\n[TEST 5] Zero Pair Repetition with Past Database");
{
  const pastBatches = [
    { id: "1", topic: "Đồ Ăn", words: ["苹果", "米饭", "面包", "鸡蛋", "牛奶"] },
    { id: "2", topic: "Gia Đình", words: ["爸爸", "妈妈", "哥哥", "姐姐", "弟弟"] }
  ];

  // Unique batch (0 or 1 shared word)
  const uniqueBatch = [
    { hanzi: "苹果" }, // 1 shared word with batch 1
    { hanzi: "香蕉" },
    { hanzi: "西瓜" },
    { hanzi: "葡萄" },
    { hanzi: "草莓" }
  ];
  const res1 = checkPairRepetition(uniqueBatch, pastBatches);
  assert.strictEqual(res1.passed, true, "Batch with <= 1 shared word should pass");

  // Overlapping batch (2 shared words with batch 1)
  const overlappingBatch = [
    { hanzi: "苹果" }, // shared 1
    { hanzi: "米饭" }, // shared 2 -> VIOLATION
    { hanzi: "香蕉" },
    { hanzi: "西瓜" },
    { hanzi: "葡萄" }
  ];
  const res2 = checkPairRepetition(overlappingBatch, pastBatches);
  assert.strictEqual(res2.passed, false, "Batch with >= 2 shared words must fail");
  assert.ok(res2.violations[0].includes("Trùng lặp cặp từ"), "Violation mentions pair repetition");

  // Intra-batch duplicates
  const duplicateBatch = [
    { hanzi: "苹果" },
    { hanzi: "苹果" },
    { hanzi: "西瓜" },
    { hanzi: "葡萄" },
    { hanzi: "草莓" }
  ];
  const res3 = checkPairRepetition(duplicateBatch, pastBatches);
  assert.strictEqual(res3.passed, false, "Intra-batch duplicate words must fail");
  console.log("  ✅ Passed: Zero pair repetition and intra-batch uniqueness verified");
}

// 6. Full Deterministic Audit
console.log("\n[TEST 6] Full Deterministic Audit on 5-Word Batch");
{
  const validIdea = {
    topic: "Đồ Dùng Nhà Bếp",
    level: "HSK 1",
    words: [
      { hanzi: "筷子", pinyin: "kuài zi", meaning: "Đôi đũa" },
      { hanzi: "碗", pinyin: "wǎn", meaning: "Cái bát" },
      { hanzi: "盘子", pinyin: "pán zi", meaning: "Cái đĩa" },
      { hanzi: "勺子", pinyin: "sháo zi", meaning: "Cái thìa" },
      { hanzi: "锅", pinyin: "guō", meaning: "Cái nồi" }
    ]
  };
  const auditRes = auditIdeaDeterministic(validIdea, []);
  assert.strictEqual(auditRes.passed, true, "Valid 5-word batch should pass deterministic audit");
  assert.strictEqual(auditRes.error_reasons.length, 0, "No error reasons");
  console.log("  ✅ Passed: Full deterministic audit passed for valid batch");
}

// 7. Retry Protocol Simulation
console.log("\n[TEST 7] Retry Protocol Simulation (Attempt 1, 2 -> Strike 3)");
{
  const mockEnv = {
    GITHUB_TOKEN: "mock_gh_token",
    GITHUB_REPO_OWNER: "naadld",
    GITHUB_REPO_NAME: "lele2vid",
    GEMINI_API_KEYS: "key1,key2,key3,key4,key5,key6",
    TELEGRAM_BOT_TOKEN: "",
    TELEGRAM_CHAT_ID: "1187577977",
    SPREADSHEET_ID: "mock_sheet_id",
    SHEET_TAB_NAME: "pinyin"
  };
  const config = getConfig(mockEnv);

  const invalidIdea = {
    row_id: "test_row_99",
    topic: "Đồ Ăn & Thức Uống", // VIOLATION: compound topic
    level: "HSK 1",
    words: [
      { hanzi: "國語", pinyin: "guó", meaning: "Language" } // Multiple violations
    ]
  };

  // Attempt 1 (retry_count = 0)
  const resAttempt1 = await processGatekeeperIdea(mockEnv, config, { ...invalidIdea, retry_count: 0 });
  assert.strictEqual(resAttempt1.success, false);
  assert.strictEqual(resAttempt1.status, "Rejected");
  assert.strictEqual(resAttempt1.action, "call_step_2");
  assert.strictEqual(resAttempt1.retry_count, 1);
  console.log("  ✅ Passed: Attempt 1 returned action='call_step_2' with retry_count=1");

  // Attempt 2 (retry_count = 1)
  const resAttempt2 = await processGatekeeperIdea(mockEnv, config, { ...invalidIdea, retry_count: 1 });
  assert.strictEqual(resAttempt2.success, false);
  assert.strictEqual(resAttempt2.status, "Rejected");
  assert.strictEqual(resAttempt2.action, "call_step_2");
  assert.strictEqual(resAttempt2.retry_count, 2);
  console.log("  ✅ Passed: Attempt 2 returned action='call_step_2' with retry_count=2");

  // Attempt 3 (retry_count = 2 -> Strike 3)
  const resAttempt3 = await processGatekeeperIdea(mockEnv, config, { ...invalidIdea, retry_count: 2 });
  assert.strictEqual(resAttempt3.success, false);
  assert.strictEqual(resAttempt3.status, "Deleted");
  assert.strictEqual(resAttempt3.action, "delete_row");
  assert.strictEqual(resAttempt3.retry_count, 3);
  console.log("  ✅ Passed: Attempt 3 (Strike 3) returned action='delete_row' and halted retries");
}

console.log("\n===============================================================");
console.log("🎉 ALL TESTS PASSED SUCCESSFULLY (100% VERIFIED)");
console.log("===============================================================");

