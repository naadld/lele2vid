import re
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("PreRenderValidator")

try:
    import opencc
    _opencc_converter = opencc.OpenCC('t2s')
except ImportError:
    _opencc_converter = None

class PreRenderValidator:
    """
    Pre-Render Gatekeeper: Validates batch data BEFORE Manim video rendering.
    Enforces strict layout, linguistic, and metadata constraints.
    """
    def __init__(self):
        self.max_hanzi_len = 4        # Max 4 hanzi chars to avoid template card overflow
        self.max_pinyin_len = 28      # Max pinyin string length
        self.max_meaning_len = 35     # Max Vietnamese meaning length (1-line limit)
        self.required_word_count = 5  # Must have exactly 5 words

    def validate_batch(self, batch: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate complete batch data. Returns (is_valid, list_of_error_reasons).
        """
        errors = []
        topic = batch.get("topic", "")
        level = batch.get("level", "")
        words = batch.get("words", [])
        metadata = batch.get("metadata", "")

        # 1. Check Topic & Level
        if not topic or len(topic.strip()) < 3:
            errors.append("Chủ đề (Topic) quá ngắn hoặc bị rỗng.")
        if not level:
            errors.append("Cấp độ (Level) bị rỗng.")

        # 2. Check Word Count
        if len(words) != self.required_word_count:
            errors.append(f"Số lượng từ không đúng ({len(words)}/5 từ).")

        # 3. Check Each Word
        for idx, w in enumerate(words, start=1):
            hanzi = w.get("hanzi", "").strip()
            pinyin = w.get("pinyin", "").strip()
            hidden_pinyin = w.get("hidden_pinyin", "").strip()
            meaning = w.get("meaning", "").strip()

            # 3a. Hanzi Check
            if not hanzi:
                errors.append(f"Từ #{idx}: Chữ Hán (Hanzi) bị rỗng.")
                continue

            if len(hanzi) > self.max_hanzi_len:
                errors.append(f"Từ #{idx} '{hanzi}': Quá dài ({len(hanzi)} ký tự, tối đa {self.max_hanzi_len} chữ) gây tràn khung.")

            # Ensure all characters are Chinese
            if not all('\u4e00' <= char <= '\u9fff' for char in hanzi):
                errors.append(f"Từ #{idx} '{hanzi}': Chứa ký tự không phải chữ Hán.")

            # Simplified Chinese Check
            if _opencc_converter:
                simplified = _opencc_converter.convert(hanzi)
                if simplified != hanzi:
                    errors.append(f"Từ #{idx} '{hanzi}': Chứa chữ Phồn thể (Nên dùng: '{simplified}').")

            # 3b. Pinyin Check
            if not pinyin:
                errors.append(f"Từ #{idx} '{hanzi}': Pinyin bị rỗng.")
            else:
                if len(pinyin) > self.max_pinyin_len:
                    errors.append(f"Từ #{idx} '{hanzi}': Pinyin '{pinyin}' quá dài ({len(pinyin)} ký tự) làm lệch template.")

                # Syllable count match
                pinyin_syllables = [s for s in pinyin.split() if s.strip()]
                if len(pinyin_syllables) != len(hanzi):
                    errors.append(f"Từ #{idx} '{hanzi}': Số âm tiết Pinyin ({len(pinyin_syllables)}) không khớp với số chữ Hán ({len(hanzi)}).")

            # 3c. Meaning (Nghĩa tiếng Việt) Check
            if not meaning:
                errors.append(f"Từ #{idx} '{hanzi}': Nghĩa tiếng Việt bị rỗng.")
            elif len(meaning) > self.max_meaning_len:
                errors.append(f"Từ #{idx} '{hanzi}': Nghĩa '{meaning}' quá dài ({len(meaning)} ký tự, tối đa {self.max_meaning_len}) gây rớt dòng lệch thẻ.")

        # 4. Check Metadata Column
        if not metadata or metadata.strip() == "":
            errors.append("Cột Metadata bị rỗng.")
        elif metadata.startswith("#ERROR"):
            errors.append("Cột Metadata bị lỗi công thức #ERROR!.")
        elif not ("YOUTUBE" in metadata.upper() or "[YOUTUBE]" in metadata.upper()):
            errors.append("Cột Metadata thiếu cấu trúc YouTube Shorts.")

        is_valid = len(errors) == 0
        return is_valid, errors
