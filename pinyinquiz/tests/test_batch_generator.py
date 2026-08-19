import pytest
from unittest.mock import patch, MagicMock
from scripts.generate_daily_batches import (
    format_single_batch_payload,
    post_to_cloudflare_webhook,
    FALLBACK_VOCAB_BANK,
    run_batch_mode,
    run_single_row_mode
)
from src.llm_client import parse_gemini_keys, mask_key
from src.pre_render_validator import PreRenderValidator

@pytest.fixture
def validator():
    return PreRenderValidator()

class TestFormatBatchPayload:
    """Test batch payload formatting contract for Cloudflare Worker and Google Sheet."""

    def test_format_single_batch_payload_contract(self):
        raw_words = [
            {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},
            {"hanzi": "米饭", "pinyin": "mǐ fàn", "meaning": "Cơm trắng"},
            {"hanzi": "面条", "pinyin": "miàn tiáo", "meaning": "Bát mì"},
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
        assert payload["words"][0]["pinyin"] == "píng guǒ"
        assert "_" in payload["words"][0]["hidden_pinyin"]
        assert "YOUTUBE SHORTS" in payload["metadata"]
        assert payload["retry_count"] == 0

        assert sheet_row[0] == "10"
        assert sheet_row[1] == "Món Ăn Hằng Ngày"
        assert sheet_row[2] == "HSK 1"
        assert sheet_row[3] == "Pending"
        assert len(sheet_row) >= 15


class TestWebhookIntegration:
    """Test webhook transmission to Cloudflare Worker."""

    @patch("requests.post")
    def test_post_to_cloudflare_webhook_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "status": "Pending", "row_id": "10"}
        mock_post.return_value = mock_resp

        payload = {"row_id": "10", "topic": "Món Ăn", "level": "HSK 1", "words": []}
        ok, res = post_to_cloudflare_webhook("https://example.com/api/receive-ideas", payload)

        assert ok is True
        assert res.get("status") == "Pending"
        assert mock_post.called

    @patch("requests.post")
    def test_post_to_cloudflare_webhook_rejection(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 422
        mock_resp.json.return_value = {"success": False, "error": "Gatekeeper rejected"}
        mock_post.return_value = mock_resp

        payload = {"row_id": "10", "topic": "Compound Topic & Bad", "level": "HSK 1", "words": []}
        ok, res = post_to_cloudflare_webhook("https://example.com/api/receive-ideas", payload)

        assert ok is False
        assert mock_post.called


class TestFallbackVocabBankPurity:
    """Verify that every fallback vocabulary bank entry complies 100% with PreRenderValidator."""

    def test_all_fallback_entries_pass_pre_render_validator(self, validator):
        for topic, level, words in FALLBACK_VOCAB_BANK:
            raw_words = [{"hanzi": hz, "pinyin": py, "meaning": mean} for hz, py, mean in words]
            payload, _ = format_single_batch_payload(
                row_id="fb_test",
                topic=topic,
                level=level,
                raw_words=raw_words
            )
            is_valid, errors = validator.validate_batch(payload)
            assert is_valid is True, f"Fallback batch '{topic}' failed validation: {errors}"


class TestKeyRotationAndExecutionModes:
    """Test dynamic key parsing, zero-secret masking, and batch execution modes."""

    def test_key_parsing_and_masking(self):
        raw_keys = "AIzaSyKey111111111111111111111111111, AIzaSyKey222222222222222222222222222"
        keys = parse_gemini_keys(raw_keys)
        assert len(keys) == 2
        masked1 = mask_key(keys[0])
        assert masked1.startswith("AIzaSy")
        assert masked1.endswith("****")
        assert len(masked1) <= 15

    def test_run_batch_mode_dry_run(self):
        # Dry-run generates batch without network calls
        run_batch_mode(
            count=2,
            gemini_keys=["AIzaSyFakeKey12345678901234567890"],
            delay_seconds=0,
            update_sheet=False,
            dry_run=True
        )

    def test_run_single_row_mode_dry_run(self):
        # Single-row dry-run generates 1 replacement row
        run_single_row_mode(
            row_id="42",
            rejected_topic="Đồ Ăn & Thức Uống",
            error_reasons="Chứa ký tự ghép nối (&)",
            gemini_keys=["AIzaSyFakeKey12345678901234567890"],
            update_sheet=False,
            dry_run=True
        )
