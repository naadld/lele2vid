import pytest
from src.pinyin_utils import (
    hanzi_to_pinyin_list,
    hanzi_to_full_pinyin,
    pinyin_to_hidden_pinyin,
    prepare_word_tuple
)

class TestHanziToPinyinConversion:
    """Test converting Hanzi to tone-marked pinyin list and string."""

    @pytest.mark.parametrize("hanzi,expected_list", [
        ("苹果", ["píng", "guǒ"]),
        ("老师", ["lǎo", "shī"]),
        ("学校", ["xué", "xiào"]),
        ("喜欢", ["xǐ", "huān"]),
        ("中国", ["zhōng", "guó"]),
        ("出租车", ["chū", "zū", "chē"]),
        ("水", ["shuǐ"])
    ])
    def test_hanzi_to_pinyin_list(self, hanzi, expected_list):
        result = hanzi_to_pinyin_list(hanzi)
        assert result == expected_list, f"Expected {expected_list} for '{hanzi}', got {result}"

    @pytest.mark.parametrize("hanzi,expected_pinyin", [
        ("苹果", "píng guǒ"),
        ("米饭", "mǐ fàn"),
        ("面条", "miàn tiáo"),
        ("喝水", "hē shuǐ"),
        ("吃饭", "chī fàn")
    ])
    def test_hanzi_to_full_pinyin(self, hanzi, expected_pinyin):
        result = hanzi_to_full_pinyin(hanzi)
        assert result == expected_pinyin


class TestPinyinToHiddenPinyin:
    """Test generating game-ready hidden pinyin with underscore masking."""

    @pytest.mark.parametrize("full_pinyin,expected_hidden", [
        ("píng guǒ", "p _ _ _   g _ _"),
        ("lǎo shī", "l _ _   s _ _"),
        ("xué xiào", "x _ _   x _ _ _"),
        ("xǐ huān", "x _   h _ _ _"),
        ("zhōng guó", "z _ _ _ _   g _ _"),
        ("péng you", "p _ _ _   y _ _")
    ])
    def test_first_char_each_syllable_mode(self, full_pinyin, expected_hidden):
        result = pinyin_to_hidden_pinyin(full_pinyin, reveal_mode="first_char_each_syllable")
        assert result == expected_hidden, f"For '{full_pinyin}', expected '{expected_hidden}' but got '{result}'"

    def test_first_char_only_mode(self):
        full_pinyin = "píng guǒ"
        result = pinyin_to_hidden_pinyin(full_pinyin, reveal_mode="first_char_only")
        # Only the very first char of whole word is revealed: 'p _ _ _   _ _ _'
        assert result.startswith("p")
        assert result == "p _ _ _   _ _ _"

    def test_empty_and_whitespace_input(self):
        assert pinyin_to_hidden_pinyin("") == ""
        assert pinyin_to_hidden_pinyin("   ") == ""

    def test_single_syllable(self):
        result = pinyin_to_hidden_pinyin("shuǐ")
        assert result == "s _ _ _"

    def test_pinyin_with_umlaut_vowel(self):
        # nǚ ér (ü with 3rd tone)
        result = pinyin_to_hidden_pinyin("nǚ ér")
        assert result == "n _   é _"


class TestPrepareWordTuple:
    """Test tuple preparation for scene generation and sheet storage."""

    def test_automatic_generation(self):
        h, fp, hp = prepare_word_tuple("苹果")
        assert h == "苹果"
        assert fp == "píng guǒ"
        assert hp == "p _ _ _   g _ _"

    def test_custom_pinyin_override(self):
        h, fp, hp = prepare_word_tuple("衣服", custom_pinyin="yī fu")
        assert h == "衣服"
        assert fp == "yī fu"
        assert hp == "y _   f _"

    def test_custom_hidden_override(self):
        h, fp, hp = prepare_word_tuple("桌子", custom_hidden="z _ _ _   z _")
        assert h == "桌子"
        assert fp == "zhuō zi"
        assert hp == "z _ _ _   z _"

    def test_whitespace_stripping(self):
        h, fp, hp = prepare_word_tuple("  中国  ", custom_pinyin="  zhōng guó  ")
        assert h == "中国"
        assert fp == "zhōng guó"
        assert hp == "z _ _ _ _   g _ _"
