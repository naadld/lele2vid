import os
import json
import pytest
from unittest.mock import patch, MagicMock
from src.llm_client import (
    mask_key,
    parse_gemini_keys,
    parse_json_from_llm,
    call_gemini_api,
    generate_hsk_topics_with_llm,
    generate_single_replacement_topic
)

def test_mask_key():
    assert mask_key("") == "None"
    assert mask_key(None) == "None"
    assert mask_key("short") == "****"
    assert mask_key("AIzaSy1234567890abcdef") == "AIzaSy...****"
    assert mask_key("AQ.Ab8XYZ123456") == "AQ.Ab8...****"

def test_parse_gemini_keys(monkeypatch):
    # From comma string
    keys = parse_gemini_keys("key1, key2, key3")
    assert keys == ["key1", "key2", "key3"]

    # From list
    keys = parse_gemini_keys(["keyA", "keyB, keyC"])
    assert keys == ["keyA", "keyB", "keyC"]

    # From env var
    monkeypatch.setenv("GEMINI_API_KEYS", "env1, env2, env3")
    keys = parse_gemini_keys(None)
    assert keys == ["env1", "env2", "env3"]

def test_parse_json_from_llm():
    # 1. Plain JSON array
    raw1 = '[{"topic": "HSK 1", "level": "HSK 1", "words": []}]'
    assert parse_json_from_llm(raw1) == [{"topic": "HSK 1", "level": "HSK 1", "words": []}]

    # 2. Markdown codeblock ```json ... ```
    raw2 = "Here is your JSON:\n```json\n[{\"topic\": \"Test\", \"level\": \"HSK 2\", \"words\": []}]\n```\nHope it helps!"
    assert parse_json_from_llm(raw2) == [{"topic": "Test", "level": "HSK 2", "words": []}]

    # 3. Object with trailing commas
    raw3 = "```json\n{\n  \"topic\": \"Obj\",\n  \"level\": \"HSK 1\",\n  \"words\": [\n    {\"hanzi\": \"书\", \"pinyin\": \"shū\", \"meaning\": \"Sách\",},\n  ],\n}\n```"
    res3 = parse_json_from_llm(raw3)
    assert res3 is not None
    assert res3["topic"] == "Obj"

    # 4. Embedded array in text without code fences
    raw4 = "Some text before [{\"topic\": \"Embedded\", \"level\": \"HSK 3\", \"words\": []}] some text after"
    assert parse_json_from_llm(raw4) == [{"topic": "Embedded", "level": "HSK 3", "words": []}]

    # 5. Invalid JSON
    assert parse_json_from_llm("Not a json at all") is None

@patch("requests.post")
def test_call_gemini_api_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '[{"topic": "Mock Topic", "level": "HSK 1", "words": []}]'}]
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    res = call_gemini_api(
        prompt="test prompt",
        api_keys=["fake_key_1"],
        model="gemini-3.7-flash"
    )
    assert res is not None
    assert "Mock Topic" in res
    assert mock_post.called

@patch("requests.post")
def test_call_gemini_api_key_rotation_on_429(mock_post):
    # Key 1 returns 429, Key 2 returns 200
    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.text = "Quota exceeded"

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": '[{"topic": "Key2 Topic", "level": "HSK 1", "words": []}]'}]
                }
            }
        ]
    }

    mock_post.side_effect = [resp_429, resp_200]

    res = call_gemini_api(
        prompt="test prompt",
        api_keys=["rate_limited_key", "good_key"],
        model="gemini-3.7-flash"
    )
    assert res is not None
    assert "Key2 Topic" in res
    assert mock_post.call_count == 2

@patch("requests.post")
def test_generate_hsk_topics_with_llm(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps([
                                {
                                    "topic": "Đồ Dùng Nhà Bếp",
                                    "level": "HSK 1",
                                    "words": [
                                        {"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"},
                                        {"hanzi": "碗", "pinyin": "wǎn", "meaning": "Cái bát"},
                                        {"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"},
                                        {"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa"},
                                        {"hanzi": "锅", "pinyin": "guō", "meaning": "Cái nồi"}
                                    ]
                                }
                            ])
                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    topics = generate_hsk_topics_with_llm(
        existing_words=["苹果", "米饭"],
        count=1,
        api_keys=["valid_key_123"]
    )
    assert topics is not None
    assert len(topics) == 1
    assert topics[0]["topic"] == "Đồ Dùng Nhà Bếp"
    assert len(topics[0]["words"]) == 5

@patch("requests.post")
def test_generate_single_replacement_topic(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "topic": "Dụng Cụ Học Tập",
                                "level": "HSK 1",
                                "words": [
                                    {"hanzi": "书包", "pinyin": "shū bāo", "meaning": "Cặp sách"},
                                    {"hanzi": "铅笔", "pinyin": "qiān bǐ", "meaning": "Bút chì"},
                                    {"hanzi": "本子", "pinyin": "běn zi", "meaning": "Vở"},
                                    {"hanzi": "尺子", "pinyin": "chǐ zi", "meaning": "Thước kẻ"},
                                    {"hanzi": "橡皮", "pinyin": "xiàng pí", "meaning": "Cục tẩy"}
                                ]
                            })
                        }
                    ]
                }
            }
        ]
    }
    mock_post.return_value = mock_resp

    rep = generate_single_replacement_topic(
        existing_words=["苹果"],
        row_id="12",
        rejected_topic="Đồ Dùng & Gia Đình",
        error_reasons=["Chủ đề ghép", "Dính tiếng Anh"],
        api_keys=["test_key"]
    )
    assert rep is not None
    assert rep["topic"] == "Dụng Cụ Học Tập"
    assert len(rep["words"]) == 5
