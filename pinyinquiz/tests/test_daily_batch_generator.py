import pytest
from unittest.mock import patch, MagicMock
from scripts.generate_daily_batches import (
    format_single_batch_payload,
    post_to_cloudflare_webhook,
    FALLBACK_VOCAB_BANK
)

def test_format_single_batch_payload():
    raw_words = [
        {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},
        {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm"},
        {"hanzi": "面包", "pinyin": "miàn bāo", "meaning": "Bánh mì"},
        {"hanzi": "喝水", "pinyin": "hē shuǐ", "meaning": "Uống nước"},
        {"hanzi": "吃饭", "pinyin": "chī fàn", "meaning": "Ăn cơm"}
    ]
    payload, sheet_row = format_single_batch_payload(
        row_id="10",
        topic="Món Ăn Hằng Ngày",
        level="HSK 1",
        raw_words=raw_words,
        retry_count=0
    )

    assert payload["row_id"] == "10"
    assert payload["topic"] == "Món Ăn Hằng Ngày"
    assert payload["level"] == "HSK 1"
    assert len(payload["words"]) == 5
    assert payload["words"][0]["hanzi"] == "苹果"
    assert "_" in payload["words"][0]["hidden_pinyin"]
    assert "YOUTUBE SHORTS" in payload["metadata"]

    assert sheet_row[0] == "10"
    assert sheet_row[1] == "Món Ăn Hằng Ngày"
    assert sheet_row[2] == "HSK 1"
    assert sheet_row[3] == "Pending"

@patch("requests.post")
def test_post_to_cloudflare_webhook_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"success": True, "status": "Pending", "row_id": "10"}
    mock_post.return_value = mock_resp

    test_payload = {"row_id": "10", "topic": "Test Topic", "level": "HSK 1", "words": []}
    ok, res = post_to_cloudflare_webhook("https://fake.workers.dev/api/receive-ideas", test_payload)

    assert ok is True
    assert res.get("status") == "Pending"
    assert mock_post.called

def test_fallback_vocab_bank_integrity():
    # Ensure every entry in fallback vocab bank is valid and conforms to rules
    for topic, level, words in FALLBACK_VOCAB_BANK:
        assert len(topic) >= 3, f"Topic '{topic}' too short"
        assert "&" not in topic and " VÀ " not in topic.upper() and "+" not in topic, f"Topic '{topic}' must be single topic"
        assert len(words) == 5, f"Topic '{topic}' must have exactly 5 words"
        for hz, py, mean in words:
            assert all('\u4e00' <= c <= '\u9fff' for c in hz), f"Hanzi '{hz}' must be valid Chinese"
            assert len(py.split()) == len(hz), f"Pinyin '{py}' syllables must match Hanzi '{hz}' count"
            assert len(mean) > 0, f"Meaning for '{hz}' must not be empty"
