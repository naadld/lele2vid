import pytest
from src.metadata_generator import (
    clean_topic_display,
    generate_social_metadata,
    get_formatted_metadata_text,
    save_and_upload_metadata,
    sanitize_filename
)

def make_sample_words():
    return [
        {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},
        {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
        {"hanzi": "面条", "pinyin": "miàn tiáo", "meaning": "Bát mì"},
        {"hanzi": "喝水", "pinyin": "hē shuǐ", "meaning": "Uống nước"},
        {"hanzi": "吃饭", "pinyin": "chī fàn", "meaning": "Ăn cơm"}
    ]

class TestCleanTopicDisplay:
    """Test topic text cleaning and prefix stripping."""

    def test_strip_bullet_prefix(self):
        assert clean_topic_display("HSK 1 • Đồ Ăn Hằng Ngày") == "Đồ Ăn Hằng Ngày"
        assert clean_topic_display("HSK 2 • Thời Tiết Bốn Mùa") == "Thời Tiết Bốn Mùa"

    def test_plain_topic_without_bullet(self):
        assert clean_topic_display("Món Ăn Thân Quen") == "Món Ăn Thân Quen"


class TestGenerateSocialMetadata:
    """Test multi-platform social media metadata generation."""

    def test_youtube_metadata_structure(self):
        words = make_sample_words()
        meta = generate_social_metadata("Đồ Ăn Hằng Ngày", "HSK 1", words)
        yt = meta["youtube"]

        assert "title" in yt
        assert "description" in yt
        assert "Đoán Pinyin" in yt["title"]
        assert "#Shorts" in yt["title"]
        assert len(yt["title"]) <= 100

        # Description must contain all 5 words
        for w in words:
            assert w["hanzi"] in yt["description"]
            assert w["pinyin"] in yt["description"]
            assert w["meaning"] in yt["description"]

        # Description must include brand hashtags
        assert "#lelehoctiengtrung" in yt["description"]
        assert "#pinyinquiz" in yt["description"]
        assert "#hsk1" in yt["description"]

    def test_tiktok_metadata_structure(self):
        words = make_sample_words()
        meta = generate_social_metadata("Đồ Ăn Hằng Ngày", "HSK 1", words)
        tt = meta["tiktok"]

        assert "caption" in tt
        assert "#lelehoctiengtrung" in tt["caption"]
        assert "#pinyinquiz" in tt["caption"]
        assert "#hsk1" in tt["caption"]

    def test_facebook_reels_metadata_structure(self):
        words = make_sample_words()
        meta = generate_social_metadata("Đồ Ăn Hằng Ngày", "HSK 1", words)
        fb = meta["facebook"]

        assert "caption" in fb
        assert "#lelehoctiengtrung" in fb["caption"]
        assert "#hsk1" in fb["caption"]

    def test_formatted_text_no_leading_equal_sign(self):
        words = make_sample_words()
        text = get_formatted_metadata_text("Đồ Ăn Hằng Ngày", "HSK 1", words)

        # Must never start with '=' (avoids Google Sheets #ERROR! / #VALUE! formula execution)
        assert not text.startswith("=")
        assert "【 1. YOUTUBE SHORTS 】" in text
        assert "【 2. TIKTOK 】" in text
        assert "【 3. FACEBOOK REELS 】" in text

    def test_save_and_upload_metadata_backward_compatibility(self):
        words = make_sample_words()
        result_text = save_and_upload_metadata(
            batch_id="101",
            topic="Đồ Ăn Hằng Ngày",
            level="HSK 1",
            words=words
        )
        assert isinstance(result_text, str)
        assert "YOUTUBE SHORTS" in result_text
        assert "TIKTOK" in result_text
        assert "FACEBOOK REELS" in result_text
