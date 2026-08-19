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

        # 2b. Check Duplicate Hanzi within Batch
        hanzi_seen = set()
        for idx, w in enumerate(words, start=1):
            h_clean = w.get("hanzi", "").strip()
            if h_clean:
                if h_clean in hanzi_seen:
                    errors.append(f"Trùng lặp từ vựng trong cùng mẻ: Từ #{idx} '{h_clean}' bị lặp lại!")
                hanzi_seen.add(h_clean)

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
                    errors.append(f"Từ #{idx} '{hanzi}': Chứa chữ Phồn thể (Nên dùng Giản thể: '{simplified}').")

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

            # 3c. Hidden Pinyin Check
            if not hidden_pinyin:
                errors.append(f"Từ #{idx} '{hanzi}': Pinyin ẩn (Hidden Pinyin) bị rỗng.")
            elif "_" not in hidden_pinyin:
                errors.append(f"Từ #{idx} '{hanzi}': Pinyin ẩn '{hidden_pinyin}' không chứa ký tự gạch chân '_' để người xem đoán.")

            # 3d. Meaning (Nghĩa tiếng Việt) Check
            if not meaning:
                errors.append(f"Từ #{idx} '{hanzi}': Nghĩa tiếng Việt bị rỗng.")
            elif len(meaning) > self.max_meaning_len:
                errors.append(f"Từ #{idx} '{hanzi}': Nghĩa '{meaning}' quá dài ({len(meaning)} ký tự, tối đa {self.max_meaning_len}) gây rớt dòng lệch thẻ.")
            elif "\ufffd" in meaning or "□" in meaning:
                errors.append(f"Từ #{idx} '{hanzi}': Nghĩa '{meaning}' chứa ký tự lỗi font/encoding (□ hoặc ).")
            elif re.search(r'\b(chair|window|lamp|bookshelf|washing machine|table|door|bed|house|school|teacher|student|father|mother|brother|sister|water|apple|bread|food|drink|rice|noodle|dog|cat|car|bus|train|airplane|taxi|bicycle|happy|sad|angry|afraid|cold|hot|warm|weather|rain|snow|sun|wind|cloud|sky|money|cheap|expensive|buy|sell|eat|drink|watch|look|see|listen|speak|read|write|learn|study|work|office|hospital|doctor|nurse)\b', meaning, re.IGNORECASE):
                errors.append(f"Từ #{idx} '{hanzi}': Nghĩa '{meaning}' bị dính Tiếng Anh (Yêu cầu 100% Nghĩa Tiếng Việt).")

        # 3e. Check Topic Artifacts
        if "\ufffd" in topic or "□" in topic:
            errors.append(f"Chủ đề '{topic}' chứa ký tự lỗi font/encoding (□ hoặc ).")

        # 4. Strict Metadata Inspection (Kiểm tra đầy đủ 3 nền tảng + Hashtags)
        if not metadata or metadata.strip() == "":
            errors.append("Cột Metadata bị rỗng (Chưa có nội dung đăng bài).")
        elif metadata.startswith("#ERROR") or metadata.startswith("#VALUE") or metadata.startswith("#REF"):
            errors.append("Cột Metadata bị lỗi công thức Google Sheets (#ERROR! / #VALUE!).")
        else:
            meta_upper = metadata.upper()
            if "YOUTUBE" not in meta_upper:
                errors.append("Metadata thiếu phần tiêu đề & mô tả cho YouTube Shorts.")
            if "TIKTOK" not in meta_upper:
                errors.append("Metadata thiếu phần Caption cho TikTok.")
            if "FACEBOOK" not in meta_upper and "REELS" not in meta_upper:
                errors.append("Metadata thiếu phần Caption cho Facebook Reels.")
            if "#LELEHOCTIENGTRUNG" not in meta_upper and "#PINYIN" not in meta_upper:
                errors.append("Metadata thiếu bộ Hashtags chuẩn nhận diện thương hiệu kênh (#lelehoctiengtrung, #pinyinquiz).")

        is_valid = len(errors) == 0
        return is_valid, errors
