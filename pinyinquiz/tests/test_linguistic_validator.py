import pytest
from src.pre_render_validator import (
    PreRenderValidator,
    TONE_VOWELS,
    VALID_NEUTRAL_SYLLABLES,
    STRICT_TRADITIONAL_CHARS,
    ENGLISH_FORBIDDEN_WORDS
)

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
        "row_id": "val_test_01",
        "topic": "Món Ăn Hằng Ngày",
        "level": "HSK 1",
        "words": default_words,
        "metadata": "YOUTUBE: Tiêu đề video\nTIKTOK: Caption\nFACEBOOK REELS: Caption\n#lelehoctiengtrung #pinyinquiz"
    }
    batch.update(kwargs)
    return batch


class TestSingleTopicValidation:
    """Validate Single Topic rule against all compound topic connectors and edge cases."""

    @pytest.mark.parametrize("compound_topic", [
        "Đồ Ăn & Thức Uống",
        "Đồ Ăn + Nước Uống",
        "Trường Học / Bệnh Viện",
        "Thời Tiết \\ Mùa Màng",
        "Gia Đình VÀ Bạn Bè",
        "Gia Đình va Bạn Bè",
        "Food And Drink",
        "Trái cây hoặc Rau củ",
        "Trái cây hoac Rau củ",
        "Nhà cửa với Trường học",
        "Nhà cửa voi Trường học",
        "Du lịch cùng Bạn bè",
        "Quần áo kèm Phụ kiện",
        "Chủ Đề 1, Chủ Đề 2",
        "Từ Vựng Đời Sống v.v.",
        "Từ Vựng Đời Sống etc"
    ])
    def test_reject_compound_topics(self, validator, compound_topic):
        batch = make_valid_batch(topic=compound_topic)
        is_valid, errors = validator.validate_batch(batch)
        assert not is_valid, f"Compound topic '{compound_topic}' must be rejected!"
        assert any("đơn" in err or "ghép" in err or "ký tự" in err or "nối" in err for err in errors)

    @pytest.mark.parametrize("valid_topic", [
        "Món Ăn Hằng Ngày",
        "Đồ Dùng Học Tập",
        "Phương Tiện Giao Thông",
        "Thời Tiết Bốn Mùa",
        "Cảm Xúc Thường Thấy",
        "Địa Điểm Thân Quen",
        "HSK 1 • Gia Đình Thân Yêu",
        "HSK 2, Bài 1"  # HSK comma exception
    ])
    def test_accept_valid_single_topics(self, validator, valid_topic):
        batch = make_valid_batch(topic=valid_topic)
        is_valid, errors = validator.validate_batch(batch)
        assert is_valid is True, f"Valid single topic '{valid_topic}' should pass, but got errors: {errors}"


class TestSimplifiedChineseEnforcement:
    """Validate 100% Simplified Chinese rule (strictly 0% Traditional characters)."""

    @pytest.mark.parametrize("trad_hanzi,meaning", [
        ("蘋果", "Quả táo"),
        ("傳統", "Truyền thống"),
        ("學習", "Học tập"),
        ("中國", "Trung Quốc"),
        ("飛機", "Máy bay"),
        ("學生", "Học sinh"),
        ("國家", "Quốc gia"),
        ("學校", "Trường học"),
        ("買書", "Mua sách"),
        ("醫生", "Bác sĩ"),
        ("電腦", "Máy tính")
    ])
    def test_reject_traditional_chinese_characters(self, validator, trad_hanzi, meaning):
        batch = make_valid_batch()
        batch["words"][0] = {
            "hanzi": trad_hanzi,
            "pinyin": "píng guǒ" if len(trad_hanzi) == 2 else "yī",
            "hidden_pinyin": "p _   g _",
            "meaning": meaning
        }
        is_valid, errors = validator.validate_batch(batch)
        assert not is_valid, f"Traditional Chinese '{trad_hanzi}' must be rejected!"
        assert any("Phồn thể" in err for err in errors)

    def test_accept_standard_simplified_vocabulary(self, validator):
        simplified_words = [
            {"hanzi": "衣服", "pinyin": "yī fu", "hidden_pinyin": "y _   f _", "meaning": "Quần áo"},
            {"hanzi": "桌子", "pinyin": "zhuō zi", "hidden_pinyin": "z _ _ _   z _", "meaning": "Cái bàn"},
            {"hanzi": "椅子", "pinyin": "yǐ zi", "hidden_pinyin": "y _   z _", "meaning": "Cái ghế"},
            {"hanzi": "书包", "pinyin": "shū bāo", "hidden_pinyin": "s _ _   b _ _", "meaning": "Cặp sách"},
            {"hanzi": "医生", "pinyin": "yī shēng", "hidden_pinyin": "y _   s _ _ _ _", "meaning": "Bác sĩ"}
        ]
        batch = make_valid_batch(words=simplified_words)
        is_valid, errors = validator.validate_batch(batch)
        assert is_valid is True, f"Standard simplified words must pass, but got: {errors}"


class TestVietnameseMeaningPurity:
    """Validate 100% Vietnamese meaning rule (strictly 0 English words/loanwords)."""

    @pytest.mark.parametrize("english_meaning", [
        "Quả táo (apple)",
        "Cái bàn (table)",
        "Chuyến bus",
        "Xe taxi",
        "Uống coffee",
        "Uống milk",
        "Đôi chopsticks",
        "Quyển book",
        "Người teacher",
        "Chiếc laptop",
        "Cửa sổ (window)",
        "Con dog",
        "Con cat",
        "Cái chair",
        "Uống water",
        "Cái phone",
        "Chiếc computer",
        "Cái camera"
    ])
    def test_reject_english_loanwords_and_annotations(self, validator, english_meaning):
        batch = make_valid_batch()
        batch["words"][0]["meaning"] = english_meaning
        is_valid, errors = validator.validate_batch(batch)
        assert not is_valid, f"Meaning with English '{english_meaning}' must be rejected!"
        assert any("Tiếng Anh" in err or "tiếng Anh" in err for err in errors)

    @pytest.mark.parametrize("pure_vn_meaning", [
        "Quả táo",
        "Cái bàn",
        "Cái ghế",
        "Cửa sổ",
        "Xe buýt",
        "Xe tắc xi",
        "Cà phê sữa đá",
        "Sữa tươi",
        "Đôi đũa",
        "Quyển sách",
        "Thầy giáo",
        "Máy tính xách tay",
        "Cái ly",
        "Ly nước mát"
    ])
    def test_accept_pure_vietnamese_meanings(self, validator, pure_vn_meaning):
        batch = make_valid_batch()
        batch["words"][0]["meaning"] = pure_vn_meaning
        is_valid, errors = validator.validate_batch(batch)
        assert is_valid is True, f"Pure Vietnamese meaning '{pure_vn_meaning}' should pass, but got: {errors}"


class TestPinyinToneMarkEnforcement:
    """Validate Pinyin tone marks on syllables and syllable count match."""

    @pytest.mark.parametrize("plain_ascii_pinyin", [
        "ping guo",
        "lao shi",
        "xue sheng",
        "zhong guo",
        "chi fan",
        "shui"
    ])
    def test_reject_plain_ascii_pinyin_without_tones(self, validator, plain_ascii_pinyin):
        batch = make_valid_batch()
        hanzi = "西瓜" if len(plain_ascii_pinyin.split()) == 2 else "水"
        batch["words"][0]["hanzi"] = hanzi
        batch["words"][0]["pinyin"] = plain_ascii_pinyin
        is_valid, errors = validator.validate_batch(batch)
        assert not is_valid, f"Plain ASCII pinyin '{plain_ascii_pinyin}' must be rejected!"
        assert any("thanh điệu" in err for err in errors)

    @pytest.mark.parametrize("valid_pinyin,hanzi", [
        ("píng guǒ", "苹果"),
        ("yī fu", "衣服"),      # neutral tone 'fu'
        ("zhuō zi", "桌子"),    # neutral tone 'zi'
        ("bà ba", "爸爸"),      # neutral tone 'ba'
        ("tā men", "他们"),     # neutral tone 'men'
        ("xī guā", "西瓜"),
        ("chá shuǐ", "茶水")
    ])
    def test_accept_valid_tone_marked_pinyin(self, validator, valid_pinyin, hanzi):
        batch = make_valid_batch()
        batch["words"][0]["hanzi"] = hanzi
        batch["words"][0]["pinyin"] = valid_pinyin
        is_valid, errors = validator.validate_batch(batch)
        assert is_valid is True, f"Valid pinyin '{valid_pinyin}' for '{hanzi}' should pass, but got: {errors}"

    @pytest.mark.parametrize("mismatched_pinyin,hanzi", [
        ("píng", "苹果"),              # 1 syllable vs 2 hanzi
        ("píng guǒ hóng", "苹果"),     # 3 syllables vs 2 hanzi
        ("chū zū", "出租车"),          # 2 syllables vs 3 hanzi
        ("shuǐ guǒ", "水")             # 2 syllables vs 1 hanzi
    ])
    def test_reject_syllable_count_mismatch(self, validator, mismatched_pinyin, hanzi):
        batch = make_valid_batch()
        batch["words"][0]["hanzi"] = hanzi
        batch["words"][0]["pinyin"] = mismatched_pinyin
        is_valid, errors = validator.validate_batch(batch)
        assert not is_valid, f"Pinyin '{mismatched_pinyin}' for '{hanzi}' must fail syllable match!"
        assert any("không khớp" in err for err in errors)


class TestLayoutAndEncodingConstraints:
    """Validate layout constraints, encoding artifacts, word counts, and metadata."""

    def test_reject_oversized_hanzi(self, validator):
        batch = make_valid_batch()
        batch["words"][0]["hanzi"] = "公共汽车站台"  # 6 chars > 4 max
        batch["words"][0]["pinyin"] = "gōng gòng qì chē zhàn tái"
        is_valid, errors = validator.validate_batch(batch)
        assert not is_valid
        assert any("Quá dài" in err for err in errors)

    def test_reject_oversized_meaning(self, validator):
        batch = make_valid_batch()
        batch["words"][0]["meaning"] = "Đây là phần giải thích nghĩa tiếng Việt quá dài vượt quá giới hạn ba mươi lăm ký tự"
        is_valid, errors = validator.validate_batch(batch)
        assert not is_valid
        assert any("quá dài" in err for err in errors)

    def test_reject_encoding_artifacts(self, validator):
        batch = make_valid_batch()
        batch["words"][0]["meaning"] = "Quả t\ufffdo"
        is_valid, errors = validator.validate_batch(batch)
        assert not is_valid
        assert any("lỗi font/encoding" in err for err in errors)

        batch_topic_err = make_valid_batch(topic="Món Ăn □ Đời Sống")
        is_valid_t, errors_t = validator.validate_batch(batch_topic_err)
        assert not is_valid_t
        assert any("lỗi font/encoding" in err for err in errors_t)

    def test_reject_hidden_pinyin_without_underscore(self, validator):
        batch = make_valid_batch()
        batch["words"][0]["hidden_pinyin"] = "p i n g   g u o"  # No '_'
        is_valid, errors = validator.validate_batch(batch)
        assert not is_valid
        assert any("gạch chân" in err for err in errors)

    def test_reject_incomplete_metadata(self, validator):
        # Missing TikTok
        batch = make_valid_batch(metadata="YOUTUBE: Tiêu đề\nFACEBOOK REELS: Caption\n#lelehoctiengtrung #pinyinquiz")
        is_valid, errors = validator.validate_batch(batch)
        assert not is_valid
        assert any("TikTok" in err for err in errors)

        # Missing brand hashtags
        batch2 = make_valid_batch(metadata="YOUTUBE: Title\nTIKTOK: Caption\nFACEBOOK REELS: Caption")
        is_valid2, errors2 = validator.validate_batch(batch2)
        assert not is_valid2
        assert any("Hashtags" in err for err in errors2)
