import re
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger("PreRenderValidator")

try:
    import opencc
    _opencc_converter = opencc.OpenCC('t2s')
except ImportError:
    _opencc_converter = None

TONE_VOWELS = set("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ")

VALID_NEUTRAL_SYLLABLES = {
    "de", "le", "ma", "ba", "ne", "zi", "men", "tou", "fu", "er",
    "ya", "la", "ge", "huo", "bian", "shang", "xia", "li", "you",
    "me", "xi", "sheng", "huan", "bai", "liang", "shi", "fan", "shu",
    "nao", "jie", "di", "zhe", "guo", "wa", "qian", "hou", "mian",
    "dao", "hu", "sa", "luo", "dian", "kuai"
}

STRICT_TRADITIONAL_CHARS = set(
    "侶個們傘傳傷價優兒動員問單國圓圖報場孫學實寫對導師帳帶幣幫幾廚廣廳彎後愛戶據數斷書會東業樂樓樣機檢櫃歡氣涼溫漢灣為無熱燈爲爺環產畫當療發稅筆紙結統經綠網練總習聲聽腦臥臺與舊萬藍藥蘋處號衛裡褲襪見視親記診試話認語說誰課請謝識護讀變讓豬貓貴買費賓賣質車輛輪這週進遊過遠遲選邊鄰醫銀錢錶鏡鐘鐵長門開間關陰陽雙雞難雲電霧響頭頻題顏風颱飛飯飲飽餃餅餓館馬髮魚鮮鳥鴨鵝鹹麵麼點齒龍"
)

ENGLISH_FORBIDDEN_WORDS = [
    "chair", "table", "window", "door", "bed", "lamp", "bookshelf", "desk", "cup", "glass",
    "bottle", "bowl", "plate", "chopsticks", "spoon", "fork", "knife", "mirror", "clock",
    "watch", "key", "bag", "wallet", "box", "fan", "fridge", "refrigerator",
    "television", "radio", "washing machine", "air conditioner",
    "laptop", "computer", "phone", "smartphone", "telephone", "camera", "screen",
    "keyboard", "mouse", "headphone", "earphone", "tablet", "app", "software", "website",
    "internet", "wifi", "email", "video", "audio", "game",
    "apple", "banana", "orange", "grape", "watermelon", "strawberry", "fruit", "vegetable",
    "rice", "noodle", "bread", "meat", "beef", "pork", "chicken", "fish", "egg", "soup",
    "cake", "candy", "sugar", "salt", "pepper", "water", "tea", "coffee", "milk", "beer",
    "wine", "juice", "drink", "food",
    "car", "bus", "taxi", "train", "plane", "airplane", "flight", "airport", "station",
    "bicycle", "bike", "motorbike", "motorcycle", "boat", "ship", "subway", "metro",
    "ticket", "hotel", "tour", "trip",
    "teacher", "student", "doctor", "nurse", "driver", "worker", "engineer", "lawyer",
    "police", "father", "mother", "dad", "mom", "brother", "sister", "son", "daughter",
    "baby", "child", "children", "family", "friend", "boy", "girl", "man", "woman",
    "person", "people",
    "dog", "cat", "bird", "fish", "duck", "chicken", "pig", "cow", "horse", "sheep",
    "monkey", "tiger", "lion", "elephant", "bear", "snake", "rabbit", "mouse", "rat",
    "animal", "pet",
    "house", "home", "room", "kitchen", "bedroom", "bathroom", "office", "building",
    "school", "university", "hospital", "bank", "park", "store", "shop", "market",
    "supermarket", "restaurant", "cinema", "theatre", "city", "town", "country",
    "eat", "drink", "sleep", "wake", "walk", "run", "swim", "fly", "drive", "ride",
    "read", "write", "speak", "listen", "hear", "see", "look", "watch", "buy", "sell",
    "pay", "cost", "work", "study", "learn", "teach", "sing", "dance", "play", "cook",
    "clean", "wash", "open", "close", "start", "stop", "wait", "help", "meet", "love",
    "like", "hate", "want", "need", "think", "know", "understand",
    "good", "bad", "big", "small", "large", "little", "tall", "short", "long", "fat",
    "thin", "hot", "cold", "warm", "cool", "fast", "slow", "new", "old", "young",
    "clean", "dirty", "happy", "sad", "angry", "afraid", "scared", "tired", "hungry",
    "thirsty", "rich", "poor", "cheap", "expensive", "easy", "hard", "difficult",
    "beautiful", "pretty", "ugly", "red", "blue", "green", "yellow", "black", "white",
    "brown", "pink", "purple",
    "sun", "moon", "star", "sky", "cloud", "rain", "snow", "wind", "tree", "flower",
    "leaf", "grass", "mountain", "river", "sea", "ocean", "lake", "weather", "spring",
    "summer", "autumn", "fall", "winter", "time", "hour", "minute", "second", "day",
    "night", "morning", "afternoon", "evening", "today", "tomorrow", "yesterday", "week",
    "month", "year",
    "cafe", "book", "pen", "pencil", "notebook", "ruler", "eraser", "shoes", "shirt",
    "dress", "skirt", "pants", "jacket", "coat", "hat", "cap", "socks", "glasses",
    "ring", "money", "dollar"
]

_ENGLISH_REGEX = re.compile(r'\b(' + '|'.join(re.escape(w) for w in ENGLISH_FORBIDDEN_WORDS) + r')\b', re.IGNORECASE)
_BRACKETED_LATIN_REGEX = re.compile(r'[\(\[\{][a-zA-Z\s]+[\)\]\}]')

class PreRenderValidator:
    """Pre-render validator for VocabVNQuiz."""

    @staticmethod
    def validate_batch(batch_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        topic = batch_data.get("topic", "").strip()
        if not topic:
            errors.append("Topic is missing.")

        words = batch_data.get("words", [])
        if len(words) != 5:
            errors.append(f"Số lượng từ không đúng ({len(words)}/5 từ).")

        seen_hanzi = set()
        seen_meaning = set()

        for idx, w in enumerate(words, start=1):
            hz = w.get("hanzi", "").strip()
            py = w.get("pinyin", "").strip()
            mean = w.get("meaning", "").strip()

            if not hz:
                errors.append(f"Từ #{idx}: Thiếu chữ Hán.")
            if not py:
                errors.append(f"Từ #{idx}: Thiếu Pinyin.")
            if not mean:
                errors.append(f"Từ #{idx}: Thiếu nghĩa tiếng Việt.")

            # Check duplicate within batch
            if hz in seen_hanzi:
                errors.append(f"Từ #{idx}: Trùng chữ Hán '{hz}' trong cùng batch.")
            seen_hanzi.add(hz)

            if mean.lower() in seen_meaning:
                errors.append(f"Từ #{idx}: Trùng nghĩa tiếng Việt '{mean}' trong cùng batch.")
            seen_meaning.add(mean.lower())

            # Check Traditional Chinese
            if _opencc_converter and hz:
                simplified = _opencc_converter.convert(hz)
                if simplified != hz:
                    errors.append(f"Từ #{idx} '{hz}': Chứa chữ Hán Phồn thể (Yêu cầu Giản thể '{simplified}').")
            else:
                for c in hz:
                    if c in STRICT_TRADITIONAL_CHARS:
                        errors.append(f"Từ #{idx} '{hz}': Ký tự '{c}' là chữ Phồn thể.")

            # Check English in meaning
            if mean:
                found_en = _ENGLISH_REGEX.findall(mean)
                if found_en:
                    errors.append(f"Từ #{idx}: Nghĩa tiếng Việt '{mean}' chứa từ tiếng Anh cấm: {found_en}.")

        return len(errors) == 0, errors
