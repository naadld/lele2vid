import pytest
from src.pre_render_validator import PreRenderValidator

@pytest.fixture
def validator():
    return PreRenderValidator()

def make_valid_batch(**kwargs):
    default_words = [
        {"hanzi": "苹果", "pinyin": "píng guǒ", "hidden_pinyin": "p _ _ _   g _ _", "meaning": "Quả táo"},
        {"hanzi": "米饭", "pinyin": "mǐ fàn", "hidden_pinyin": "m _   f _ _", "meaning": "Cơm trắng"},
        {"hanzi": "面条", "pinyin": "miàn tiáo", "hidden_pinyin": "m _ _ _   t _ _ _", "meaning": "Bát mì"},
        {"hanzi": "喝水", "pinyin": "hē shuǐ", "hidden_pinyin": "h _   s _ _ _", "meaning": "Uống nước"},
        {"hanzi": "吃饭", "pinyin": "chī fàn", "hidden_pinyin": "c _ _   f _ _", "meaning": "Ăn cơm"}
    ]
    batch = {
        "row_id": "test_01",
        "topic": "Món Ăn Hằng Ngày",
        "level": "HSK 1",
        "words": default_words,
        "metadata": "YOUTUBE: Tiêu đề\nTIKTOK: Caption\nFACEBOOK REELS: Caption\n#lelehoctiengtrung #pinyinquiz"
    }
    batch.update(kwargs)
    return batch


# ============================================================================
# SUITE 1: SINGLE TOPIC RULE
# ============================================================================
class TestSingleTopicRule:
    @pytest.mark.parametrize("compound_topic", [
        "Đồ Ăn & Thức Uống",
        "Gia Đình VÀ Bạn Bè",
        "Trường Học + Bệnh Viện",
        "Thời Tiết / Mùa Màng",
        "Thời Tiết \\ Khí Hậu",
        "Food And Drink",
        "đồ ăn và thức uống",
        "Trái cây hoặc Rau củ",
        "Nhà cửa với Trường học",
        "Chủ Đề 1, Chủ Đề 2"
    ])
    def test_compound_topic_rejection(self, validator, compound_topic):
        batch = make_valid_batch(topic=compound_topic)
        is_valid, errors = validator.validate_batch(batch)
        print(f"\n[TOPIC TEST] '{compound_topic}' -> is_valid={is_valid}, errors={errors}")
        assert not is_valid, f"Compound topic '{compound_topic}' must be rejected by validator!"
        assert any("đơn" in err or "ghép" in err or "ký tự" in err or "nối" in err for err in errors)


# ============================================================================
# SUITE 2: LANGUAGE PURITY (NO ENGLISH IN VIETNAMESE MEANING)
# ============================================================================
class TestLanguagePurity:
    @pytest.mark.parametrize("english_meaning,expected_flag", [
        ("Quả táo (apple)", True),
        ("Cái bàn (table)", True),
        ("Chuyến bus", True),
        ("Xe taxi", True),
        ("Uống coffee", True),
        ("Uống milk", True),
        ("Đôi chopsticks", True),
        ("Quyển book", True),
        ("Người teacher", True),
        ("Chiếc laptop", True),
        ("Cửa sổ (window)", True)
    ])
    def test_english_meaning_detection(self, validator, english_meaning, expected_flag):
        batch = make_valid_batch()
        batch["words"][0]["meaning"] = english_meaning
        is_valid, errors = validator.validate_batch(batch)
        print(f"\n[MEANING TEST] '{english_meaning}' -> is_valid={is_valid}, errors={errors}")
        assert not is_valid, f"Meaning with English '{english_meaning}' must be rejected by validator!"

    def test_pure_vietnamese_meanings_pass(self, validator):
        batch = make_valid_batch()
        is_valid, errors = validator.validate_batch(batch)
        assert is_valid is True
        assert len(errors) == 0


# ============================================================================
# SUITE 3: CHARACTER SET (SIMPLIFIED VS TRADITIONAL CHINESE)
# ============================================================================
class TestCharacterSet:
    @pytest.mark.parametrize("trad_word,trad_hanzi", [
        ({"hanzi": "蘋果", "pinyin": "píng guǒ", "hidden_pinyin": "p _ _   g _ _", "meaning": "Quả táo"}, "蘋果"),
        ({"hanzi": "傳統", "pinyin": "chuán tǒng", "hidden_pinyin": "c _ _ _ _   t _ _ _", "meaning": "Truyền thống"}, "傳統"),
        ({"hanzi": "學習", "pinyin": "xué xí", "hidden_pinyin": "x _ _   x _", "meaning": "Học tập"}, "學習"),
        ({"hanzi": "中國", "pinyin": "zhōng guó", "hidden_pinyin": "z _ _ _ _   g _ _", "meaning": "Trung Quốc"}, "中國"),
        ({"hanzi": "車", "pinyin": "chē", "hidden_pinyin": "c _ _", "meaning": "Xe cộ"}, "車")
    ])
    def test_traditional_chinese_rejection(self, validator, trad_word, trad_hanzi):
        batch = make_valid_batch()
        batch["words"][0] = trad_word
        is_valid, errors = validator.validate_batch(batch)
        print(f"\n[TRADITIONAL TEST] '{trad_hanzi}' -> is_valid={is_valid}, errors={errors}")
        assert not is_valid, f"Traditional Chinese word '{trad_hanzi}' must be rejected!"
        assert any("Phồn thể" in err for err in errors)

    def test_simplified_chinese_passes(self, validator):
        simplified_words = [
            {"hanzi": "衣服", "pinyin": "yī fu", "hidden_pinyin": "y _   f _", "meaning": "Quần áo"},
            {"hanzi": "桌子", "pinyin": "zhuō zi", "hidden_pinyin": "z _ _ _   z _", "meaning": "Cái bàn"},
            {"hanzi": "椅子", "pinyin": "yǐ zi", "hidden_pinyin": "y _   z _", "meaning": "Cái ghế"},
            {"hanzi": "书包", "pinyin": "shū bāo", "hidden_pinyin": "s _ _   b _ _", "meaning": "Cặp sách"},
            {"hanzi": "医生", "pinyin": "yī shēng", "hidden_pinyin": "y _   s _ _ _ _", "meaning": "Bác sĩ"}
        ]
        batch = make_valid_batch(words=simplified_words)
        is_valid, errors = validator.validate_batch(batch)
        print(f"\n[SIMPLIFIED TEST] Valid words -> is_valid={is_valid}, errors={errors}")
        assert is_valid is True, f"Standard simplified words must pass, but got errors: {errors}"


# ============================================================================
# SUITE 4: PINYIN TONE & SYLLABLE COUNT
# ============================================================================
class TestPinyinToneAndSyllables:
    @pytest.mark.parametrize("hanzi,pinyin,case_desc", [
        ("苹果", "píng", "Syllables < Hanzi chars (1 vs 2)"),
        ("出租车", "chū zū", "Syllables < Hanzi chars (2 vs 3)"),
        ("水", "shuǐ guǒ", "Syllables > Hanzi chars (2 vs 1)"),
        ("老师", "lǎo shī hǎo", "Syllables > Hanzi chars (3 vs 2)")
    ])
    def test_pinyin_syllable_mismatch_rejection(self, validator, hanzi, pinyin, case_desc):
        batch = make_valid_batch()
        batch["words"][0]["hanzi"] = hanzi
        batch["words"][0]["pinyin"] = pinyin
        is_valid, errors = validator.validate_batch(batch)
        print(f"\n[PINYIN SYLLABLE TEST] '{hanzi}' ('{pinyin}') ({case_desc}) -> is_valid={is_valid}, errors={errors}")
        assert not is_valid, f"Pinyin mismatch '{case_desc}' must fail!"
        assert any("không khớp" in err for err in errors)

    def test_missing_pinyin_tone_marks(self, validator):
        # Plain ASCII without tones: 'ping guo' instead of 'píng guǒ'
        batch = make_valid_batch()
        batch["words"][0]["pinyin"] = "ping guo"
        is_valid, errors = validator.validate_batch(batch)
        print(f"\n[PINYIN TONE TEST] 'ping guo' without tone marks -> is_valid={is_valid}, errors={errors}")
        assert not is_valid, "Plain ASCII pinyin without tone marks must be rejected!"
        assert any("thanh điệu" in err for err in errors)


# ============================================================================
# SUITE 5: PAIR REPETITION & INTRA-BATCH DUPLICATES
# ============================================================================
class TestDuplicatesAndWordCount:
    def test_intra_batch_duplicate_hanzi(self, validator):
        batch = make_valid_batch()
        batch["words"][1]["hanzi"] = batch["words"][0]["hanzi"] # Duplicate "苹果"
        is_valid, errors = validator.validate_batch(batch)
        print(f"\n[DUPLICATE TEST] Duplicate '苹果' -> is_valid={is_valid}, errors={errors}")
        assert not is_valid
        assert any("Trùng lặp" in err for err in errors)

    def test_word_count_not_five(self, validator):
        batch = make_valid_batch()
        batch["words"] = batch["words"][:4] # Only 4 words
        is_valid, errors = validator.validate_batch(batch)
        assert not is_valid
        assert any("Số lượng từ không đúng" in err for err in errors)
