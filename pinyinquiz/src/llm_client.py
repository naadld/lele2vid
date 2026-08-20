import os
import re
import json
import logging
import requests
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger("LLMClient")

DEFAULT_LLM_URL = os.getenv("LLM_BASE_URL", "http://vpsg24gb:20130/v1")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
FALLBACK_GEMINI_MODELS = ["gemini-3.7-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
GEMINI_ENDPOINT_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def mask_key(key: Optional[str]) -> str:
    """
    Mask an API key for safe logging (e.g. AQ.Ab8...**** or AIzaSy...****).
    Never logs full plaintext keys.
    """
    if not key:
        return "None"
    k = str(key).strip()
    if len(k) <= 8:
        return "****"
    return f"{k[:6]}...****"


def parse_gemini_keys(keys_input: Optional[Union[str, List[str]]] = None) -> List[str]:
    """
    Parse ephemeral Gemini API keys from argument, list, or environment variables.
    Supports comma-separated strings or list of keys.
    """
    keys = []
    
    # 1. From direct input argument
    if keys_input:
        if isinstance(keys_input, list):
            for item in keys_input:
                if item and isinstance(item, str):
                    for sub in item.split(","):
                        clean = sub.strip()
                        if clean and clean not in keys:
                            keys.append(clean)
        elif isinstance(keys_input, str):
            for sub in keys_input.split(","):
                clean = sub.strip()
                if clean and clean not in keys:
                    keys.append(clean)

    # 2. From environment variables (GEMINI_API_KEYS, GEMINI_API_KEY, GOOGLE_API_KEY)
    if not keys:
        env_raw = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        if env_raw:
            for sub in env_raw.split(","):
                clean = sub.strip()
                if clean and clean not in keys:
                    keys.append(clean)

    return keys


def parse_json_from_llm(content: str) -> Optional[Any]:
    """
    Robust JSON parser for LLM responses.
    Handles Markdown code fences (```json ... ```), raw arrays/objects,
    and trailing comma cleanups.
    """
    if not content or not isinstance(content, str):
        return None

    cleaned = content.strip()

    # 1. Check for markdown code fences ```json ... ``` or ``` ... ```
    if "```" in cleaned:
        code_block_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
        matches = code_block_pattern.findall(cleaned)
        for match in matches:
            candidate = match.strip()
            try:
                parsed = json.loads(candidate)
                if parsed is not None:
                    return parsed
            except json.JSONDecodeError:
                # Try fixing trailing commas before closing brackets
                fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
                try:
                    parsed = json.loads(fixed)
                    if parsed is not None:
                        return parsed
                except json.JSONDecodeError:
                    continue

    # 2. Direct JSON load attempt
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 3. Find outermost JSON array [...]
    start_arr = cleaned.find("[")
    end_arr = cleaned.rfind("]")
    if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
        candidate = cleaned[start_arr:end_arr + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

    # 4. Find outermost JSON object {...}
    start_obj = cleaned.find("{")
    end_obj = cleaned.rfind("}")
    if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
        candidate = cleaned[start_obj:end_obj + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

    return None


def call_gemini_api(
    prompt: str,
    system_prompt: Optional[str] = None,
    api_keys: Optional[List[str]] = None,
    model: str = DEFAULT_GEMINI_MODEL,
    temperature: float = 0.7,
    timeout: int = 60
) -> Optional[str]:
    """
    Direct Google AI Studio Gemini API call with key rotation and model failover.
    Endpoint: https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}
    """
    keys = parse_gemini_keys(api_keys)
    if not keys:
        logger.warning("No Gemini API keys provided for direct Google AI Studio call.")
        return None

    candidate_models = [model]
    for fb in FALLBACK_GEMINI_MODELS:
        if fb not in candidate_models:
            candidate_models.append(fb)

    for key_idx, key in enumerate(keys):
        masked = mask_key(key)
        for cur_model in candidate_models:
            url = f"{GEMINI_ENDPOINT_BASE}/{cur_model}:generateContent?key={key}"
            logger.info(f"Calling Google AI Studio (Model: {cur_model}, Key [{key_idx + 1}/{len(keys)}]: {masked})...")

            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": prompt}]
                    }
                ],
                "generationConfig": {
                    "temperature": temperature,
                    "responseMimeType": "application/json"
                }
            }

            if system_prompt:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_prompt}]
                }

            headers = {
                "Content-Type": "application/json"
            }

            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=(5.0, float(timeout)))
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        # Filter out thought parts if thinking model
                        text_parts = [p.get("text", "") for p in parts if not p.get("thought") and p.get("text")]
                        if not text_parts and parts:
                            text_parts = [parts[0].get("text", "")]
                        full_text = "".join(text_parts).strip()
                        if full_text:
                            logger.info(f" Google AI Studio ({cur_model}) returned valid response ({len(full_text)} chars).")
                            return full_text
                    logger.warning(f"Google AI Studio returned 200 but no valid parts in candidates: {data}")
                elif resp.status_code == 429:
                    logger.warning(f"Google AI Studio Rate Limit (429) for key {masked}. Rotating to next key...")
                    break  # Break model loop and switch to next key
                elif resp.status_code in (400, 403, 404):
                    logger.warning(f"Google AI Studio error ({resp.status_code}) with model {cur_model} on key {masked}: {resp.text[:200]}")
                    continue  # Try next model on this key or next key
                else:
                    logger.warning(f"Google AI Studio error HTTP {resp.status_code}: {resp.text[:200]}")
            except Exception as e:
                logger.warning(f"Google AI Studio request exception on key {masked} ({cur_model}): {e}")
                continue

    logger.warning("All Google AI Studio Gemini keys/models failed.")
    return None


def call_openai_compatible_api(
    prompt: str,
    system_prompt: Optional[str] = None,
    base_url: str = DEFAULT_LLM_URL,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.7,
    timeout: int = 5
) -> Optional[str]:
    """
    Fallback call to local or OpenAI-compatible endpoint (e.g. vpsg24gb:20130).
    """
    api_url = f"{base_url.rstrip('/')}/chat/completions"
    logger.info(f"Connecting to OpenAI-compatible LLM service at {api_url} (Model: {model})...")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False
    }

    try:
        resp = requests.post(api_url, json=payload, timeout=(3.0, float(timeout)))
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "").strip()
            if content:
                logger.info(f" OpenAI-compatible LLM ({model}) returned valid response ({len(content)} chars).")
                return content
    except Exception as e:
        logger.warning(f"Could not connect to OpenAI-compatible LLM ({api_url}): {e}")

    return None


def build_system_prompt() -> str:
    """
    Strict linguistic and structural system prompt conforming to Gatekeeper 1 standards.
    Supports diverse levels across HSK 1, HSK 2, and HSK 3.
    """
    return (
        "Bạn là chuyên gia ngôn ngữ tiếng Trung và biên tập viên trưởng của kênh 'Lê Lê Học Tiếng Trung' (@lelehoctiengtrung).\n"
        "Nhiệm vụ của bạn là tạo các bộ từ vựng luyện tập Pinyin HSK 1, HSK 2 hoặc HSK 3 hấp dẫn, chuẩn xác, gần gũi với đời sống thực tế.\n\n"
        "QUY TẮC BẮT BUỘC (TUÂN THỦ 100% TIÊU CHUẨN GATEKEEPER 1):\n"
        "1. 100% Chữ Giản Thể (Simplified Chinese): Tuyệt đối không dùng chữ Phồn thể.\n"
        "2. Chủ đề đơn (Single Topic Only): Tên chủ đề ngắn gọn (3-7 từ), KHÔNG dùng từ nối (&, VÀ, +, /, VÀ CẢ).\n"
        "3. 100% Nghĩa Tiếng Việt thuần túy: Tuyệt đối không chứa từ tiếng Anh (chair, table, dog, cat, car, water,...).\n"
        "4. Pinyin chuẩn xác: Đầy đủ dấu thanh điệu (ā, á, ǎ, à, ē, é, ě, è, ī, í, ǐ, ì, ō, ó, ǒ, ò, ū, ú, ǔ, ù, ǖ, ǘ, ǚ, ǜ), số âm tiết Pinyin phải khớp 1-1 với số chữ Hán.\n"
        "5. Phân bổ trình độ HSK đa dạng: Trải đều phong phú giữa HSK 1, HSK 2 và HSK 3, không cố định duy nhất một cấp độ HSK 1.\n"
        "6. Mỗi bộ chủ đề gồm đúng 5 từ vựng, mỗi từ dài từ 1 đến 4 chữ Hán.\n"
        "7. Bắt buộc trả về định dạng JSON thuần túy (Array hoặc Object theo yêu cầu), không thêm bất kỳ lời dẫn hay giải thích nào."
    )


def generate_hsk_topics_with_llm(
    existing_words: Optional[List[str]] = None,
    count: int = 5,
    api_keys: Optional[Union[str, List[str]]] = None,
    model: str = DEFAULT_GEMINI_MODEL,
    existing_topics: Optional[List[str]] = None,
    target_level: Optional[str] = None,
    base_url: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Generate non-repeating HSK vocabulary batches using Direct Google AI Studio Gemini API
    with fallback to OpenAI-compatible endpoint.
    Supports specific target_level (HSK 1, HSK 2, HSK 3) or diverse multi-level distribution.
    """
    system_prompt = build_system_prompt()

    used_words_sample = ", ".join(list(existing_words)[-100:]) if existing_words else "chưa có"
    used_topics_sample = ", ".join(list(existing_topics)[-30:]) if existing_topics else "chưa có"

    if target_level:
        level_instruction = f"CẤP ĐỘ MỤC TIÊU: {target_level}. Hãy tạo các bộ từ vựng đúng chuẩn trình độ {target_level}."
        example_level = target_level
    else:
        level_instruction = "CẤP ĐỘ MỤC TIÊU: ĐA DẠNG HSK 1, HSK 2 VÀ HSK 3. Hãy phân bổ luân phiên, xen kẽ giữa HSK 1, HSK 2 và HSK 3 (Ví dụ: Batch 1: HSK 1, Batch 2: HSK 2, Batch 3: HSK 3... Tuyệt đối KHÔNG cố định một cấp độ)."
        example_level = "HSK 2"

    user_prompt = f"""Hãy tạo đúng {count} bộ chủ đề từ vựng tiếng Trung mới lạ, thiết thực và hấp dẫn.
{level_instruction}
Mỗi bộ chủ đề phải có đúng 5 từ vựng.

NGỮ CẢNH LOẠI TRỪ (NEGATIVE CONTEXT - TUYỆT ĐỐI KHÔNG TRÙNG LẶP HOẶC TƯƠNG TỰ):
- Các chủ đề đã có gần đây: [{used_topics_sample}]
- Các từ vựng đã xuất hiện gần đây: [{used_words_sample}]

Định dạng JSON yêu cầu (Trả về duy nhất 1 JSON Array):
[
  {{
    "topic": "Đồ Dùng Nhà Bếp",
    "level": "{example_level}",
    "words": [
      {{"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"}},
      {{"hanzi": "碗", "pinyin": "wǎn", "meaning": "Cái bát / chén"}},
      {{"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"}},
      {{"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa / muỗng"}},
      {{"hanzi": "锅", "pinyin": "guō", "meaning": "Cái nồi / chảo"}}
    ]
  }}
]
"""

    # 1. Try Direct Google AI Studio Gemini API
    raw_content = None
    keys = parse_gemini_keys(api_keys)
    if keys:
        raw_content = call_gemini_api(
            prompt=user_prompt,
            system_prompt=system_prompt,
            api_keys=keys,
            model=model,
            temperature=0.7
        )

    # 2. Fallback to OpenAI-compatible endpoint if Gemini failed
    if not raw_content:
        logger.info("Trying fallback to OpenAI-compatible LLM endpoint...")
        raw_content = call_openai_compatible_api(
            prompt=user_prompt,
            system_prompt=system_prompt,
            base_url=base_url or DEFAULT_LLM_URL,
            model="gemini-2.5-flash"
        )

    if not raw_content:
        logger.warning("Failed to obtain raw content from all LLM providers.")
        return None

    parsed = parse_json_from_llm(raw_content)
    if isinstance(parsed, list) and len(parsed) > 0:
        logger.info(f" Successfully generated and parsed {len(parsed)} HSK batches!")
        return parsed
    elif isinstance(parsed, dict) and "topic" in parsed:
        logger.info(" Parsed 1 batch (dict converted to list).")
        return [parsed]

    logger.warning("LLM response could not be parsed into a valid list of topic batches.")
    return None


def generate_single_replacement_topic(
    existing_words: Optional[List[str]] = None,
    row_id: str = "1",
    rejected_topic: str = "",
    error_reasons: Optional[Union[str, List[str]]] = None,
    api_keys: Optional[Union[str, List[str]]] = None,
    target_level: Optional[str] = None,
    model: str = DEFAULT_GEMINI_MODEL
) -> Optional[Dict[str, Any]]:
    """
    Generate exactly 1 replacement HSK batch for a rejected row (Step 2 Targeted Re-Generation).
    Explicitly provides the previous rejected topic and error reasons to avoid repeating mistakes.
    """
    system_prompt = build_system_prompt()

    used_sample = ", ".join(list(existing_words)[-100:]) if existing_words else "chưa có"

    if isinstance(error_reasons, list):
        errors_text = " | ".join(error_reasons)
    else:
        errors_text = str(error_reasons or "Không rõ")

    level_req = f"Trình độ mục tiêu: {target_level}" if target_level else "Trình độ: Đa dạng linh hoạt giữa HSK 1, HSK 2 hoặc HSK 3"

    user_prompt = f"""Dòng #{row_id} trước đó đã bị Cloudflare Gatekeeper TỪ CHỐI do vi phạm các tiêu chuẩn sau:
- Chủ đề bị từ chối: "{rejected_topic or 'Chưa có'}"
- Nguyên nhân vi phạm cụ thể: "{errors_text}"
- {level_req}

YÊU CẦU TÁI SINH DÒNG #{row_id}:
Hãy tạo DUY NHẤT 1 bộ chủ đề từ vựng tiếng Trung (HSK 1, HSK 2 hoặc HSK 3) hoàn toàn MỚI để thay thế dòng #{row_id}.
Tuyệt đối KHẮC PHỤC TRIỆT ĐỂ tất cả các lỗi vi phạm nêu trên:
- Tên chủ đề đơn lẻ, hấp dẫn, không dùng từ ghép hay liên từ nối (&, VÀ, +).
- Đúng 5 từ vựng, 100% Giản thể, 100% Nghĩa tiếng Việt, Pinyin chuẩn âm tiết và dấu thanh điệu.
- Không trùng lặp với các từ vựng đã có: [{used_sample}].

Định dạng JSON yêu cầu (Trả về duy nhất 1 JSON Object):
{{
  "topic": "Đồ Dùng Học Tập",
  "level": "{target_level or 'HSK 2'}",
  "words": [
    {{"hanzi": "书包", "pinyin": "shū bāo", "meaning": "Cặp sách"}},
    {{"hanzi": "铅笔", "pinyin": "qiān bǐ", "meaning": "Bút chì"}},
    {{"hanzi": "本子", "pinyin": "běn zi", "meaning": "Vở / Sổ tay"}},
    {{"hanzi": "尺子", "pinyin": "chǐ zi", "meaning": "Thước kẻ"}},
    {{"hanzi": "橡皮", "pinyin": "xiàng pí", "meaning": "Cục tẩy / gôm"}}
  ]
}}
"""

    raw_content = None
    keys = parse_gemini_keys(api_keys)
    if keys:
        raw_content = call_gemini_api(
            prompt=user_prompt,
            system_prompt=system_prompt,
            api_keys=keys,
            model=model,
            temperature=0.7
        )

    if not raw_content:
        logger.info("Trying fallback to OpenAI-compatible LLM endpoint for single row replacement...")
        raw_content = call_openai_compatible_api(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model="gemini-2.5-flash"
        )

    if not raw_content:
        logger.warning(f"Failed to generate replacement topic for row #{row_id}.")
        return None

    parsed = parse_json_from_llm(raw_content)
    if isinstance(parsed, dict) and "words" in parsed and "topic" in parsed:
        logger.info(f" Successfully generated replacement topic for row #{row_id}: '{parsed.get('topic')}'")
        return parsed
    elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
        logger.info(f" Successfully generated replacement topic (from array) for row #{row_id}: '{parsed[0].get('topic')}'")
        return parsed[0]

    logger.warning(f"Could not parse valid single topic object for row #{row_id} from output: {raw_content[:200]}")
    return None
