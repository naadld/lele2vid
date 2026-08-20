import re
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("PreRenderValidator")

try:
    import opencc
    _opencc_converter = opencc.OpenCC('t2s')
except ImportError:
    _opencc_converter = None

# Tone vowels in standard Pinyin
TONE_VOWELS = set("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ")

# Legitimate neutral-tone syllables when in context of tone-marked words or particles
VALID_NEUTRAL_SYLLABLES = {
    "de", "le", "ma", "ba", "ne", "zi", "men", "tou", "fu", "er",
    "ya", "la", "ge", "huo", "bian", "shang", "xia", "li", "you",
    "me", "xi", "sheng", "huan", "bai", "liang", "shi", "fan", "shu",
    "nao", "jie", "di", "zhe", "guo", "wa", "qian", "hou", "mian",
    "dao", "hu", "sa", "luo", "dian", "kuai"
}

# Strict fallback list of Traditional characters for environments without opencc or double assurance
STRICT_TRADITIONAL_CHARS = set(
    "侶個們傘傳傷價優兒動員問單國圓圖報場孫學實寫對導師帳帶幣幫幾廚廣廳彎後愛戶據數斷書會東業樂樓樣機檢櫃歡氣涼溫漢灣為無熱燈爲爺環產畫當療發稅筆紙結統經綠網練總習聲聽腦臥臺與舊萬藍藥蘋處號衛裡褲襪見視親記診試話認語說誰課請謝識護讀變讓豬貓貴買費賓賣質車輛輪這週進遊過遠遲選邊鄰醫銀錢錶鏡鐘鐵長門開間關陰陽雙雞難雲電霧響頭頻題顏風颱飛飯飲飽餃餅餓館馬髮魚鮮鳥鴨鵝鹹麵麼點齒龍"
)

# Comprehensive English forbidden words list
ENGLISH_FORBIDDEN_WORDS = [
    # Household & Objects
    "chair", "table", "window", "door", "bed", "lamp", "bookshelf", "desk", "cup", "glass",
    "bottle", "bowl", "plate", "chopsticks", "spoon", "fork", "knife", "mirror", "clock",
    "watch", "key", "bag", "wallet", "box", "fan", "fridge", "refrigerator",
    "television", "radio", "washing machine", "air conditioner",
    # Tech & Devices
    "laptop", "computer", "phone", "smartphone", "telephone", "camera", "screen",
    "keyboard", "mouse", "headphone", "earphone", "tablet", "app", "software", "website",
    "internet", "wifi", "email", "video", "audio", "game",
    # Food & Drinks
    "apple", "banana", "orange", "grape", "watermelon", "strawberry", "fruit", "vegetable",
    "rice", "noodle", "bread", "meat", "beef", "pork", "chicken", "fish", "egg", "soup",
    "cake", "candy", "sugar", "salt", "pepper", "water", "tea", "coffee", "milk", "beer",
    "wine", "juice", "drink", "food",
    # Transport & Travel
    "car", "bus", "taxi", "train", "plane", "airplane", "flight", "airport", "station",
    "bicycle", "bike", "motorbike", "motorcycle", "boat", "ship", "subway", "metro",
    "ticket", "hotel", "tour", "trip",
    # People, Occupations, Family
    "teacher", "student", "doctor", "nurse", "driver", "worker", "engineer", "lawyer",
    "police", "father", "mother", "dad", "mom", "brother", "sister", "son", "daughter",
    "baby", "child", "children", "family", "friend", "boy", "girl", "man", "woman",
    "person", "people",
    # Animals
    "dog", "cat", "bird", "fish", "duck", "chicken", "pig", "cow", "horse", "sheep",
    "monkey", "tiger", "lion", "elephant", "bear", "snake", "rabbit", "mouse", "rat",
    "animal", "pet",
    # Places & Buildings
    "house", "home", "room", "kitchen", "bedroom", "bathroom", "office", "building",
    "school", "university", "hospital", "bank", "park", "store", "shop", "market",
    "supermarket", "restaurant", "cinema", "theatre", "city", "town", "country",
    # Actions & Verbs
    "eat", "drink", "sleep", "wake", "walk", "run", "swim", "fly", "drive", "ride",
    "read", "write", "speak", "listen", "hear", "see", "look", "watch", "buy", "sell",
    "pay", "cost", "work", "study", "learn", "teach", "sing", "dance", "play", "cook",
    "clean", "wash", "open", "close", "start", "stop", "wait", "help", "meet", "love",
    "like", "hate", "want", "need", "think", "know", "understand",
    # Adjectives & Colors
    "good", "bad", "big", "small", "large", "little", "tall", "short", "long", "fat",
    "thin", "hot", "cold", "warm", "cool", "fast", "slow", "new", "old", "young",
    "clean", "dirty", "happy", "sad", "angry", "afraid", "scared", "tired", "hungry",
    "thirsty", "rich", "poor", "cheap", "expensive", "easy", "hard", "difficult",
    "beautiful", "pretty", "ugly", "red", "blue", "green", "yellow", "black", "white",
    "brown", "pink", "purple",
    # Nature & Time
    "sun", "moon", "star", "sky", "cloud", "rain", "snow", "wind", "tree", "flower",
    "leaf", "grass", "mountain", "river", "sea", "ocean", "lake", "weather", "spring",
    "summer", "autumn", "fall", "winter", "time", "hour", "minute", "second", "day",
    "night", "morning", "afternoon", "evening", "today", "tomorrow", "yesterday", "week",
    "month", "year",
    # Loanwords & Clothes & Study
    "cafe", "book", "pen", "pencil", "notebook", "ruler", "eraser", "shoes", "shirt",
    "dress", "skirt", "pants", "jacket", "coat", "hat", "cap", "socks", "glasses",
    "ring", "money", "dollar"
]

# Build compiled regex for English words
_ENGLISH_REGEX_PATTERN = r'\b(' + '|'.join(re.escape(w) for w in ENGLISH_FORBIDDEN_WORDS) + r')\b'
_ENGLISH_REGEX = re.compile(_ENGLISH_REGEX_PATTERN, re.IGNORECASE)

# Pattern for bracketed Latin / English annotations e.g. (apple), [table], (car)
_BRACKETED_LATIN_REGEX = re.compile(r'[\(\[\{][a-zA-Z\s]+[\)\]\}]')


class PreRenderValidator:
    """
    Pre-Render Gatekeeper: Validates batch data BEFORE Manim video rendering.
    Enforces strict layout, linguistic, and metadata constraints according to Pipeline 2.0.
    """
    def __init__(self):
        self.max_hanzi_len = 4        # Max 4 hanzi chars to avoid template card overflow
        self.max_pinyin_len = 28      # Max pinyin string length
        self.max_meaning_len = 35     # Max Vietnamese meaning length (1-line limit)
        self.required_word_count = 5  # Must have exactly 5 words

    def check_single_topic(self, topic: str) -> Tuple[bool, str]:
        """Validate that topic is meaningful and clean (allows natural connectors like 'và', '&', '-')."""
        if not topic or len(topic.strip()) < 2:
            return False, "Chủ đề (Topic) quá ngắn hoặc bị rỗng."
        
        if len(topic.strip()) > 50:
            return False, f"Chủ đề '{topic}' quá dài ({len(topic.strip())} ký tự, tối đa 50 ký tự)."
        
        # Check raw list delimiters like semicolons
        if ";" in topic or "|" in topic:
            return False, f"Chủ đề '{topic}' chứa ký tự phân tách danh sách (; hoặc |)."
        
        # Check etc / v.v.
        if re.search(r'(?i)(v\.v\.|v/v|\betc\b)', topic):
            return False, f"Chủ đề '{topic}' chứa ký hiệu liệt kê (v.v., etc...). Phải là 1 chủ đề rõ ràng."
        
        return True, ""

    def validate_pinyin_tones(self, pinyin_str: str, hanzi_len: int, hanzi_str: str = "") -> Tuple[bool, str]:
        """Validate pinyin syllable count and tone marks (supporting standard neutral tones & Erhua 儿化)."""
        if not pinyin_str:
            return False, "Pinyin bị rỗng."
        
        syllables = [s.strip().lower() for s in pinyin_str.split() if s.strip()]
        
        # Erhua (儿化) check: Words ending with '儿' (哪儿: nǎr, 这儿: zhèr, 那儿: nàr, 玩儿: wánr, 一点儿: yì diǎnr)
        is_erhua = bool(hanzi_str and hanzi_str.endswith("儿") and (len(syllables) == hanzi_len - 1 or any(s.endswith("r") for s in syllables)))
        
        if len(syllables) != hanzi_len and not is_erhua:
            return False, f"Số âm tiết Pinyin ({len(syllables)}) không khớp với số chữ Hán ({hanzi_len})."
        
        # In Chinese phonetics:
        # Multi-syllable word (len > 1): Must have at least 1 tone mark. Other syllables are valid neutral tones.
        # Single syllable word (len == 1): Must have a tone mark unless it is a standard particle.
        has_at_least_one_tone = any(any(c in TONE_VOWELS for c in s) for s in syllables)
        
        if not has_at_least_one_tone:
            all_neutral = all(s in VALID_NEUTRAL_SYLLABLES for s in syllables)
            if not all_neutral:
                return False, f"Pinyin '{pinyin_str}' không có dấu thanh điệu (yêu cầu Pinyin chuẩn có thanh điệu)."
        
        return True, ""

    def check_vietnamese_meaning(self, meaning: str) -> Tuple[bool, str]:
        """Validate that Vietnamese meaning is 100% Vietnamese with 0 English words."""
        if not meaning:
            return False, "Nghĩa tiếng Việt bị rỗng."
        
        if len(meaning) > self.max_meaning_len:
            return False, f"Nghĩa '{meaning}' quá dài ({len(meaning)} ký tự, tối đa {self.max_meaning_len}) gây rớt dòng lệch thẻ."
        
        if "\ufffd" in meaning or "□" in meaning:
            return False, f"Nghĩa '{meaning}' chứa ký tự lỗi font/encoding (□ hoặc \ufffd)."
        
        # Check bracketed Latin / English
        if _BRACKETED_LATIN_REGEX.search(meaning):
            return False, f"Nghĩa '{meaning}' chứa chú thích tiếng Anh trong ngoặc (Yêu cầu 100% tiếng Việt thuần túy)."
        
        # Check forbidden English words
        match = _ENGLISH_REGEX.search(meaning)
        if match:
            found_word = match.group(0)
            return False, f"Nghĩa '{meaning}' bị dính từ tiếng Anh '{found_word}' (Yêu cầu 100% Nghĩa Tiếng Việt)."
        
        return True, ""

    def check_simplified_chinese(self, hanzi: str) -> Tuple[bool, str, str]:
        """Validate Simplified Chinese character set."""
        if _opencc_converter:
            simplified = _opencc_converter.convert(hanzi)
            if simplified != hanzi:
                return False, simplified, f"Chứa chữ Phồn thể (Nên dùng Giản thể: '{simplified}')."
        
        trad_chars_found = [c for c in hanzi if c in STRICT_TRADITIONAL_CHARS]
        if trad_chars_found:
            return False, "", f"Chứa ký tự Phồn thể '{''.join(trad_chars_found)}' (Yêu cầu 100% Giản thể)."
        
        return True, hanzi, ""

    def validate_batch(self, batch: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate complete batch data. Returns (is_valid, list_of_error_reasons).
        """
        errors = []
        topic = batch.get("topic", "")
        level = batch.get("level", "")
        words = batch.get("words", [])
        metadata = batch.get("metadata", "")

        # 1. Check Topic & Single Topic Rule
        if not topic or len(topic.strip()) < 3:
            errors.append("Chủ đề (Topic) quá ngắn hoặc bị rỗng.")
        else:
            topic_valid, topic_err = self.check_single_topic(topic)
            if not topic_valid:
                errors.append(topic_err)

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

            # Simplified Chinese Check (OpenCC & Traditional character set)
            is_simplified, simp_val, simp_err = self.check_simplified_chinese(hanzi)
            if not is_simplified:
                errors.append(f"Từ #{idx} '{hanzi}': {simp_err}")

            # 3b. Pinyin Check & Tone Marks
            if not pinyin:
                errors.append(f"Từ #{idx} '{hanzi}': Pinyin bị rỗng.")
            else:
                if len(pinyin) > self.max_pinyin_len:
                    errors.append(f"Từ #{idx} '{hanzi}': Pinyin '{pinyin}' quá dài ({len(pinyin)} ký tự) làm lệch template.")

                pinyin_ok, pinyin_err = self.validate_pinyin_tones(pinyin, len(hanzi), hanzi)
                if not pinyin_ok:
                    errors.append(f"Từ #{idx} '{hanzi}': {pinyin_err}")

            # 3c. Hidden Pinyin Check
            if not hidden_pinyin:
                errors.append(f"Từ #{idx} '{hanzi}': Pinyin ẩn (Hidden Pinyin) bị rỗng.")
            elif "_" not in hidden_pinyin:
                errors.append(f"Từ #{idx} '{hanzi}': Pinyin ẩn '{hidden_pinyin}' không chứa ký tự gạch chân '_' để người xem đoán.")

            # 3d. Meaning (Nghĩa tiếng Việt) Check (100% Vietnamese, 0% English)
            meaning_ok, meaning_err = self.check_vietnamese_meaning(meaning)
            if not meaning_ok:
                errors.append(f"Từ #{idx} '{hanzi}': {meaning_err}")

        # 3e. Check Topic Artifacts
        if "\ufffd" in topic or "□" in topic:
            errors.append(f"Chủ đề '{topic}' chứa ký tự lỗi font/encoding (□ hoặc \ufffd).")

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
