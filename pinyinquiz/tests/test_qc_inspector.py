import os
import sys
import tempfile
import cv2
import numpy as np
import subprocess
import pytest
from src.qc_inspector import QCInspector, sanitize_filename, extract_gdrive_file_id

@pytest.fixture
def inspector():
    return QCInspector()

def make_qc_valid_words():
    return [
        {"hanzi": "苹果", "pinyin": "píng guǒ", "hidden_pinyin": "p _ _ _   g _ _", "meaning": "Quả táo"},
        {"hanzi": "米饭", "pinyin": "mǐ fàn", "hidden_pinyin": "m _   f _ _", "meaning": "Cơm trắng"},
        {"hanzi": "面条", "pinyin": "miàn tiáo", "hidden_pinyin": "m _ _ _   t _ _ _", "meaning": "Bát mì"},
        {"hanzi": "喝水", "pinyin": "hē shuǐ", "hidden_pinyin": "h _   s _ _ _", "meaning": "Uống nước"},
        {"hanzi": "吃饭", "pinyin": "chī fàn", "hidden_pinyin": "c _ _   f _ _", "meaning": "Ăn cơm"}
    ]

class TestQCUtilities:
    """Test helper utilities in qc_inspector."""

    def test_sanitize_filename(self):
        dirty = 'HSK 1: Món Ăn/Thức Uống * "Test" <1> | ?'
        clean = sanitize_filename(dirty)
        assert clean == "HSK 1_ Món Ăn_Thức Uống _ _Test_ _1_ _ _"
        assert not any(c in clean for c in '/\\:*?"<>|')

    def test_extract_gdrive_file_id(self):
        # Format 1: /d/<id>/view
        url1 = "https://drive.google.com/file/d/1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB/view?usp=sharing"
        assert extract_gdrive_file_id(url1) == "1Y240J5-oXA-UDm2IKvp7qCBVsRempbCB"

        # Format 2: ?id=<id>
        url2 = "https://drive.google.com/open?id=1AbCdEfGhIjKlMnOpQrStUvWxYz"
        assert extract_gdrive_file_id(url2) == "1AbCdEfGhIjKlMnOpQrStUvWxYz"

        # Invalid/empty
        assert extract_gdrive_file_id("") is None
        assert extract_gdrive_file_id(None) is None


class TestQCLinguisticChecks:
    """Test QC linguistic, encoding, and structural inspection."""

    def test_valid_words_pass(self, inspector):
        words = make_qc_valid_words()
        passed, errors = inspector.check_linguistics_and_content(words)
        assert passed is True
        assert len(errors) == 0

    def test_reject_word_count_not_five(self, inspector):
        words = make_qc_valid_words()[:3]
        passed, errors = inspector.check_linguistics_and_content(words)
        assert not passed
        assert any("Số lượng từ không đúng" in err for err in errors)

    def test_reject_duplicate_hanzi(self, inspector):
        words = make_qc_valid_words()
        words[1]["hanzi"] = "苹果"
        passed, errors = inspector.check_linguistics_and_content(words)
        assert not passed
        assert any("Trùng lặp" in err for err in errors)

    def test_reject_traditional_characters(self, inspector):
        words = make_qc_valid_words()
        words[0] = {"hanzi": "蘋果", "pinyin": "píng guǒ", "hidden_pinyin": "p _   g _", "meaning": "Quả táo"}
        passed, errors = inspector.check_linguistics_and_content(words)
        assert not passed
        assert any("Phồn thể" in err for err in errors)

    def test_reject_pinyin_syllable_mismatch(self, inspector):
        words = make_qc_valid_words()
        words[0]["pinyin"] = "píng" # 1 syllable for 2 hanzi
        passed, errors = inspector.check_linguistics_and_content(words)
        assert not passed
        assert any("không khớp" in err for err in errors)

    def test_reject_missing_hidden_pinyin_underscore(self, inspector):
        words = make_qc_valid_words()
        words[0]["hidden_pinyin"] = "p i n g   g u o" # missing '_'
        passed, errors = inspector.check_linguistics_and_content(words)
        assert not passed
        assert any("gạch chân" in err for err in errors)

    def test_reject_english_meaning_and_brackets(self, inspector):
        words = make_qc_valid_words()
        words[0]["meaning"] = "Quả táo (apple)"
        passed, errors = inspector.check_linguistics_and_content(words)
        assert not passed

        words[0]["meaning"] = "Uống coffee"
        passed2, errors2 = inspector.check_linguistics_and_content(words)
        assert not passed2

    def test_reject_encoding_artifacts(self, inspector):
        words = make_qc_valid_words()
        words[0]["meaning"] = "Quả t\ufffdo"
        passed, errors = inspector.check_linguistics_and_content(words)
        assert not passed
        assert any("lỗi font/encoding" in err for err in errors)


class TestQCPhysicalInspection:
    """Test physical video properties and QC verification."""

    def test_nonexistent_video_file(self, inspector):
        passed, errors, details = inspector.check_video_properties("/nonexistent/video.mp4")
        assert passed is False
        assert any("không tồn tại" in err for err in errors)

    def test_inspect_batch_workflow(self, inspector):
        with tempfile.TemporaryDirectory() as tmpdir:
            vid_path = os.path.join(tmpdir, "test_qc.mp4")
            # Generate a 16s vertical video with ultrafast preset
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=30",
                "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=44100:duration=16.0",
                "-t", "16.0",
                "-c:v", "libx264", "-preset", "ultrafast", "-b:v", "1M",
                "-c:a", "aac", "-b:a", "64k",
                "-pix_fmt", "yuv420p",
                vid_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

            batch = {
                "id": "1",
                "topic": "Món Ăn Hằng Ngày",
                "level": "HSK 1",
                "words": make_qc_valid_words()
            }

            result = inspector.inspect_batch(batch, vid_path)
            assert result["passed"] is True
            assert len(result["errors"]) == 0
            assert result["details"]["width"] == 1080
            assert result["details"]["height"] == 1920
            assert result["details"]["fps"] == 30.0
