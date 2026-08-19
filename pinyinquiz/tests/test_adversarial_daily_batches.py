import os
import sys
import subprocess
import pytest
from unittest.mock import patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.generate_daily_batches import (
    run_batch_mode,
    run_single_row_mode,
    format_single_batch_payload,
    FALLBACK_VOCAB_BANK
)
from src.llm_client import mask_key, parse_gemini_keys


class TestAdversarialKeyMasking:
    """Adversarial security tests for API Key masking across stdout/stderr and utils."""

    def test_mask_key_edge_cases(self):
        assert mask_key(None) == "None"
        assert mask_key("") == "None"
        # Whitespace-only or short strings return ****
        assert mask_key("   ") == "****"
        assert mask_key("123") == "****"
        assert mask_key("12345678") == "****"
        assert mask_key("AIzaSyD_SECRET_KEY_999") == "AIzaSy...****"
        assert mask_key("AQ.Ab8XYZ1234567890") == "AQ.Ab8...****"

    def test_parse_gemini_keys_adversarial_inputs(self):
        # Empty and none
        assert parse_gemini_keys(None) == []
        assert parse_gemini_keys("") == []
        assert parse_gemini_keys([]) == []

        # Complex spacing, multiple commas, duplicates
        raw = "key1,  key2, ,key3,key1,  key2 ,key4,,"
        parsed = parse_gemini_keys(raw)
        assert parsed == ["key1", "key2", "key3", "key4"]

        # List with embedded commas
        raw_list = ["keyA, keyB", " keyC ", "", "keyA"]
        parsed_list = parse_gemini_keys(raw_list)
        assert parsed_list == ["keyA", "keyB", "keyC"]

    @patch("scripts.generate_daily_batches.generate_hsk_topics_with_llm")
    def test_cli_execution_zero_secret_leak_in_stdout_and_stderr(self, mock_llm):
        """Run generate_daily_batches.py as a real subprocess and verify full keys are NEVER leaked."""
        secret_key_1 = "AIzaSyD_SECRET_KEY_VERY_CONFIDENTIAL_111"
        secret_key_2 = "AIzaSyD_SECRET_KEY_VERY_CONFIDENTIAL_222"
        keys_arg = f"{secret_key_1},{secret_key_2}"

        script_path = os.path.join(PROJECT_ROOT, "scripts", "generate_daily_batches.py")
        cmd = [
            sys.executable,
            script_path,
            "--mode", "batch",
            "--count", "2",
            "--delay", "0",
            "--gemini-keys", keys_arg,
            "--dry-run"
        ]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=PROJECT_ROOT)
        assert result.returncode == 0

        # Assert full secret keys are absent from both stdout and stderr
        assert secret_key_1 not in result.stdout
        assert secret_key_1 not in result.stderr
        assert secret_key_2 not in result.stdout
        assert secret_key_2 not in result.stderr

        # Assert masked versions ARE present in log
        assert "AIzaSy...****" in result.stdout


class TestAdversarialModuloKeyRotation:
    """Adversarial tests for 6-key rotation and modulo arithmetic."""

    def test_six_key_rotation_sequence(self):
        keys = [f"key_{i}" for i in range(1, 7)]
        count = 30
        used_keys = []

        for i in range(1, count + 1):
            key_idx = (i - 1) % len(keys)
            used_keys.append(keys[key_idx])

        # Verify pattern
        assert used_keys[0] == "key_1"
        assert used_keys[1] == "key_2"
        assert used_keys[5] == "key_6"
        assert used_keys[6] == "key_1"
        assert used_keys[29] == "key_6"
        assert len(used_keys) == 30
        assert used_keys.count("key_1") == 5
        assert used_keys.count("key_6") == 5

    def test_single_key_and_odd_key_counts(self):
        # 1 key only
        keys_1 = ["solo_key"]
        for i in range(1, 10):
            idx = (i - 1) % len(keys_1)
            assert keys_1[idx] == "solo_key"

        # 7 keys
        keys_7 = [f"k{i}" for i in range(7)]
        assert (1 - 1) % len(keys_7) == 0
        assert (7 - 1) % len(keys_7) == 6
        assert (8 - 1) % len(keys_7) == 0

    @patch("scripts.generate_daily_batches.generate_hsk_topics_with_llm")
    @patch("scripts.generate_daily_batches.load_negative_context_from_sheet")
    def test_batch_mode_dry_run_with_no_keys_graceful_fallback(self, mock_load, mock_llm):
        mock_load.return_value = ([], [], 0)
        mock_llm.return_value = None
        # Should execute without throwing ZeroDivisionError or crash
        run_batch_mode(count=2, gemini_keys=[], delay_seconds=0, dry_run=True)


class TestAdversarialCliArgumentsAndSingleRow:
    """Adversarial tests for CLI arguments and single-row re-generation."""

    def test_single_row_missing_row_id_exits_code_1(self):
        script_path = os.path.join(PROJECT_ROOT, "scripts", "generate_daily_batches.py")
        cmd = [
            sys.executable,
            script_path,
            "--mode", "single_row",
            "--dry-run"
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=PROJECT_ROOT)
        assert result.returncode == 1
        assert "Error: --row-id is required" in result.stdout or "Error: --row-id is required" in result.stderr

    @patch("scripts.generate_daily_batches.generate_single_replacement_topic")
    @patch("scripts.generate_daily_batches.load_negative_context_from_sheet")
    @patch("scripts.generate_daily_batches.send_telegram_alert")
    def test_single_row_mode_with_hash_prefix_and_fallback(self, mock_tg, mock_load, mock_llm):
        mock_load.return_value = ([], ["Gia Đình Thân Yêu"], 0)
        mock_llm.return_value = None
        # Pass row_id with '#5'
        run_single_row_mode(
            row_id="#5",
            rejected_topic="Gia Đình Thân Yêu",
            error_reasons="Chứa chữ Phồn thể",
            gemini_keys=["fake_key_123456789"],
            dry_run=True
        )
        assert mock_tg.called
        tg_text = mock_tg.call_args[0][0]
        assert "#5" in tg_text
        assert "Gia Đình Thân Yêu" in tg_text

    def test_format_single_batch_payload_contract(self):
        sample_words = [
            {"hanzi": "苹果", "pinyin": "píng guǒ", "meaning": "Quả táo"},
            {"hanzi": "香蕉", "pinyin": "xiāng jiāo", "meaning": "Quả chuối"},
            {"hanzi": "西瓜", "pinyin": "xī guā", "meaning": "Dưa hấu"},
            {"hanzi": "葡萄", "pinyin": "pú tao", "meaning": "Quả nho"},
            {"hanzi": "草莓", "pinyin": "cǎo méi", "meaning": "Quả dâu tây"}
        ]
        payload, sheet_row = format_single_batch_payload(
            row_id="42",
            topic="Trái Cây Nhiệt Đới",
            level="HSK 1",
            raw_words=sample_words,
            retry_count=1
        )

        assert payload["row_id"] == "42"
        assert payload["topic"] == "Trái Cây Nhiệt Đới"
        assert payload["level"] == "HSK 1"
        assert payload["retry_count"] == 1
        assert len(payload["words"]) == 5
        assert payload["words"][0]["hidden_pinyin"] == "p _ _ _   g _ _"

        # Check sheet row length: 4 prefix + 5 word cols + 1 meta + 4 links + 1 date + 1 note = 16 cols
        assert len(sheet_row) == 16
        assert sheet_row[0] == "42"
        assert sheet_row[1] == "Trái Cây Nhiệt Đới"
        assert sheet_row[3] == "Pending"
