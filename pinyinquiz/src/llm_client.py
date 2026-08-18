import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger("LLMClient")

DEFAULT_LLM_URL = os.getenv("LLM_BASE_URL", "http://vpsg24gb:20130/v1")
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

def generate_hsk_topics_with_llm(
    existing_words: List[str],
    count: int = 5,
    base_url: str = None,
    model: str = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Generate non-repeating HSK vocabulary batches using LLM running at vpsg24gb:20130.
    """
    base_url = base_url or os.getenv("LLM_BASE_URL", DEFAULT_LLM_URL)
    model = model or os.getenv("LLM_MODEL", DEFAULT_MODEL)
    
    api_url = f"{base_url.rstrip('/')}/chat/completions"
    logger.info(f"Connecting to LLM service at {api_url} (Model: {model})...")
    
    used_sample = ", ".join(list(existing_words)[-80:]) if existing_words else "chưa có"
    
    system_prompt = (
        "Bạn là chuyên gia ngôn ngữ tiếng Trung và biên tập nội dung kênh Lê Lệ Học Tiếng Trung.\n"
        "Nhiệm vụ của bạn là tạo các bộ từ vựng luyện tập Pinyin HSK 1 - HSK 3 hấp dẫn, chuẩn xác, gần gũi với đời sống.\n"
        "Bắt buộc trả về định dạng JSON thuần túy (không thêm bất kỳ lời dẫn hay ghi chú nào ngoài JSON)."
    )
    
    user_prompt = f"""Hãy tạo đúng {count} bộ chủ đề từ vựng tiếng Trung HSK 1, HSK 2 hoặc HSK 3 mới lạ, thực tế.
Mỗi bộ chủ đề phải có đúng 5 từ vựng.
Các từ vựng đã xuất hiện gần đây (TUYỆT ĐỐI KHÔNG TRÙNG LẶP): [{used_sample}].

Định dạng JSON yêu cầu:
[
  {{
    "topic": "HSK 1 • Tên Chủ Đề",
    "level": "HSK 1",
    "words": [
      {{"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"}},
      {{"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm"}},
      {{"hanzi": "面包", "pinyin": "miàn bāo", "meaning": "Bánh mì"}},
      {{"hanzi": "喝水", "pinyin": "hē shuǐ", "meaning": "Uống nước"}},
      {{"hanzi": "吃饭", "pinyin": "chī fàn", "meaning": "Ăn cơm"}}
    ]
  }}
]
"""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "stream": False
    }

    try:
        resp = requests.post(api_url, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        choices = data.get("choices", [])
        if not choices:
            logger.warning("LLM returned empty choices list.")
            return None
            
        content = choices[0].get("message", {}).get("content", "").strip()
        
        # Parse JSON from output
        cleaned_content = content
        if "```" in cleaned_content:
            parts = cleaned_content.split("```")
            for p in parts:
                candidate = p.strip()
                if candidate.startswith("json"):
                    candidate = candidate[4:].strip()
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, list) and len(parsed) > 0:
                        logger.info(f"✅ Successfully generated {len(parsed)} batches via LLM ({model})!")
                        return parsed
                except json.JSONDecodeError:
                    continue
        else:
            parsed = json.loads(cleaned_content)
            if isinstance(parsed, list) and len(parsed) > 0:
                logger.info(f"✅ Successfully generated {len(parsed)} batches via LLM ({model})!")
                return parsed

    except Exception as e:
        logger.warning(f"Could not connect or generate from LLM ({api_url}): {e}")
        return None

    return None
