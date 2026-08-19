import os
import sys
import tempfile
import numpy as np
import cv2
import subprocess
import pytest
from typing import Dict, Any, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.qc_inspector import QCInspector, extract_gdrive_file_id, sanitize_filename


def create_synthetic_mp4_fast(
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    fps: float = 30.0,
    duration_sec: float = 16.0,
    color: str = "blue",
    with_audio: bool = False,
    bitrate: str = "1M"
):
    """Generate synthetic MP4 video rapidly using ffmpeg lavfi."""
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c={color}:s={width}x{height}:r={fps}:d={duration_sec}"
    ]
    if with_audio:
        cmd.extend(["-f", "lavfi", "-i", f"sine=frequency=1000:sample_rate=44100:duration={duration_sec}", "-c:a", "aac", "-b:a", "64k"])
    else:
        cmd.extend(["-an"])

    cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency", "-b:v", bitrate, "-pix_fmt", "yuv420p", output_path])
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def create_opencv_test_mp4(
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    fps: float = 30.0,
    duration_sec: float = 2.0,
    frame_color_init: tuple = (50, 150, 200),
    frame_color_mid: tuple = None,
    contrast_pattern: bool = True
):
    """Generate short (1-2s) test video with custom pixel patterns for cover/contrast tests."""
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    total_frames = int(fps * duration_sec)
    temp_vid = output_path + ".raw.mp4"
    out = cv2.VideoWriter(temp_vid, fourcc, fps, (width, height))

    for i in range(total_frames):
        t = i / fps
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        base_col = frame_color_mid if (frame_color_mid and t >= 0.5) else frame_color_init
        frame[:] = base_col
        if contrast_pattern:
            cv2.rectangle(frame, (100, 200), (width - 100, height - 200), (255, 255, 255), 10)
            cv2.circle(frame, (width // 2, height // 2), 200, (0, 255, 0), -1)
            cv2.putText(frame, "TEST COVER", (150, 500), cv2.FONT_HERSHEY_SIMPLEX, 3, (0, 0, 255), 5)
        out.write(frame)
    out.release()

    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", temp_vid,
        "-c:v", "libx264", "-preset", "ultrafast", "-b:v", "2M", "-pix_fmt", "yuv420p", output_path
    ]
    subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    if os.path.exists(temp_vid):
        os.remove(temp_vid)


class TestAdversarialQCLinguistics:
    """Adversarial testing of linguistic and content structure validation."""

    def setup_method(self):
        self.inspector = QCInspector()

    def test_word_count_anomaly(self):
        # 4 words instead of 5
        words_4 = [
            {"hanzi": "爸爸", "pinyin": "bà ba", "hidden_pinyin": "b _   b _", "meaning": "Bố"},
            {"hanzi": "妈妈", "pinyin": "mā ma", "hidden_pinyin": "m _   m _", "meaning": "Mẹ"},
            {"hanzi": "儿子", "pinyin": "ér zi", "hidden_pinyin": "é _   z _", "meaning": "Con trai"},
            {"hanzi": "女儿", "pinyin": "nǚ ér", "hidden_pinyin": "n _   é _", "meaning": "Con gái"}
        ]
        passed, errs = self.inspector.check_linguistics_and_content(words_4)
        assert not passed
        assert any("Số lượng từ không đúng" in e for e in errs)

    def test_duplicate_hanzi_within_batch(self):
        words_dup = [
            {"hanzi": "苹果", "pinyin": "píng guǒ", "hidden_pinyin": "p _ _ _   g _ _", "meaning": "Quả táo"},
            {"hanzi": "香蕉", "pinyin": "xiāng jiāo", "hidden_pinyin": "x _ _ _ _   j _ _ _", "meaning": "Quả chuối"},
            {"hanzi": "苹果", "pinyin": "píng guǒ", "hidden_pinyin": "p _ _ _   g _ _", "meaning": "Quả táo lặp"},
            {"hanzi": "葡萄", "pinyin": "pú tao", "hidden_pinyin": "p _   t _ _", "meaning": "Quả nho"},
            {"hanzi": "草莓", "pinyin": "cǎo méi", "hidden_pinyin": "c _ _   m _ _", "meaning": "Quả dâu tây"}
        ]
        passed, errs = self.inspector.check_linguistics_and_content(words_dup)
        assert not passed
        assert any("Trùng lặp từ vựng trong cùng mẻ" in e for e in errs)

    def test_traditional_characters_detection(self):
        words_trad = [
            {"hanzi": "國家", "pinyin": "guó jiā", "hidden_pinyin": "g _ _   j _ _", "meaning": "Quốc gia"},
            {"hanzi": "學校", "pinyin": "xué xiào", "hidden_pinyin": "x _ _   x _ _ _", "meaning": "Trường học"},
            {"hanzi": "買書", "pinyin": "mǎi shū", "hidden_pinyin": "m _ _   s _ _", "meaning": "Mua sách"},
            {"hanzi": "飛機", "pinyin": "fēi jī", "hidden_pinyin": "f _ _   j _", "meaning": "Máy bay"},
            {"hanzi": "蘋果", "pinyin": "píng guǒ", "hidden_pinyin": "p _ _ _   g _ _", "meaning": "Quả táo"}
        ]
        passed, errs = self.inspector.check_linguistics_and_content(words_trad)
        assert not passed
        assert any("Phồn thể" in e for e in errs)

    def test_mismatched_pinyin_syllables(self):
        words_mismatch = [
            {"hanzi": "苹果", "pinyin": "píng", "hidden_pinyin": "p _ _ _", "meaning": "Quả táo"},
            {"hanzi": "香蕉", "pinyin": "xiāng jiāo shù", "hidden_pinyin": "x _ _ _ _   j _ _ _   s _ _", "meaning": "Cây chuối"},
            {"hanzi": "西瓜", "pinyin": "xī guā", "hidden_pinyin": "x _   g _ _", "meaning": "Dưa hấu"},
            {"hanzi": "葡萄", "pinyin": "pú tao", "hidden_pinyin": "p _   t _ _", "meaning": "Quả nho"},
            {"hanzi": "草莓", "pinyin": "cǎo méi", "hidden_pinyin": "c _ _   m _ _", "meaning": "Quả dâu tây"}
        ]
        passed, errs = self.inspector.check_linguistics_and_content(words_mismatch)
        assert not passed
        assert any("không khớp số chữ Hán" in e for e in errs)

    def test_encoding_artifacts_in_meaning(self):
        words_encoding = [
            {"hanzi": "桌子", "pinyin": "zhuō zi", "hidden_pinyin": "z _ _ _ _   z _", "meaning": "Cái b\ufffdn"},
            {"hanzi": "椅子", "pinyin": "yǐ zi", "hidden_pinyin": "y _   z _", "meaning": "Cái gh□"},
            {"hanzi": "杯子", "pinyin": "bēi zi", "hidden_pinyin": "b _ _   z _", "meaning": "Cái cốc"},
            {"hanzi": "电脑", "pinyin": "diàn nǎo", "hidden_pinyin": "d _ _ _   n _ _", "meaning": "Máy tính"},
            {"hanzi": "衣服", "pinyin": "yī fu", "hidden_pinyin": "y _   f _", "meaning": "Quần áo"}
        ]
        passed, errs = self.inspector.check_linguistics_and_content(words_encoding)
        assert not passed
        assert any("lỗi font/encoding" in e for e in errs)


class TestAdversarialQCPhysicalVideo:
    """Adversarial empirical testing with real synthesized corrupted/invalid MP4 videos."""

    def setup_method(self):
        self.inspector = QCInspector()
        self.temp_dir = tempfile.TemporaryDirectory()

    def teardown_method(self):
        self.temp_dir.cleanup()

    def test_nonexistent_and_corrupt_video_files(self):
        # 1. Non-existent file
        passed, errs, _ = self.inspector.check_video_properties("/path/to/nonexistent/vid.mp4")
        assert not passed
        assert "File video không tồn tại." in errs

        # 2. Corrupt / 0-byte file
        zero_file = os.path.join(self.temp_dir.name, "zero.mp4")
        with open(zero_file, "wb") as f:
            f.write(b"")
        passed, errs, _ = self.inspector.check_video_properties(zero_file)
        assert not passed

        # 3. Truncated random garbage bytes file
        garbage_file = os.path.join(self.temp_dir.name, "garbage.mp4")
        with open(garbage_file, "wb") as f:
            f.write(b"ftypmp42" + os.urandom(1024))
        passed, errs, _ = self.inspector.check_video_properties(garbage_file)
        assert not passed

    def test_horizontal_aspect_ratio_deviation(self):
        """Video is horizontal 1920x1080 instead of vertical 9:16 (1080x1920)."""
        horiz_file = os.path.join(self.temp_dir.name, "horizontal.mp4")
        create_synthetic_mp4_fast(horiz_file, width=1920, height=1080, duration_sec=16.0, fps=30.0, color="blue")

        passed, errs, details = self.inspector.check_video_properties(horiz_file)
        assert not passed
        assert any("Video nằm ngang (1920x1080)" in e for e in errs)

    def test_low_resolution_and_fps(self):
        """Video has resolution 480x640 (< 720x1280) and 15 fps (< 23 fps)."""
        low_res_file = os.path.join(self.temp_dir.name, "low_res.mp4")
        create_synthetic_mp4_fast(low_res_file, width=480, height=640, duration_sec=16.0, fps=15.0, color="red")

        passed, errs, details = self.inspector.check_video_properties(low_res_file)
        assert not passed
        assert any("Độ phân giải quá thấp" in e for e in errs)
        assert any("Tốc độ khung hình quá thấp" in e for e in errs)

    def test_duration_deviations_short_and_long(self):
        # 1. Too short (5s < 15s)
        short_file = os.path.join(self.temp_dir.name, "short.mp4")
        create_synthetic_mp4_fast(short_file, width=1080, height=1920, duration_sec=5.0, fps=30.0, color="green")
        passed, errs, _ = self.inspector.check_video_properties(short_file)
        assert not passed
        assert any("Thời lượng video quá ngắn" in e for e in errs)

        # 2. Too long (130s > 120s)
        long_file = os.path.join(self.temp_dir.name, "long.mp4")
        create_synthetic_mp4_fast(long_file, width=1080, height=1920, duration_sec=130.0, fps=30.0, color="yellow")
        passed, errs, _ = self.inspector.check_video_properties(long_file)
        assert not passed
        assert any("Thời lượng video quá dài" in e for e in errs)

    def test_pitch_black_frames_video(self):
        """Video where frames are completely pitch black (0, 0, 0)."""
        black_file = os.path.join(self.temp_dir.name, "black.mp4")
        create_synthetic_mp4_fast(
            black_file,
            width=1080,
            height=1920,
            duration_sec=16.0,
            fps=30.0,
            color="black"
        )

        passed, errs, details = self.inspector.check_video_properties(black_file)
        assert not passed
        assert any("Video bị màn hình đen" in e for e in errs)

        # Check Cover thumbnail also flags pitch black
        cover_pass, cover_errs, _ = self.inspector.check_cover_thumbnail(black_file)
        assert not cover_pass
        assert any("màn hình đen hoàn toàn" in e for e in cover_errs)

    def test_whiteout_and_low_contrast_cover_frame(self):
        """Cover frame is blinding white (255, 255, 255) and flat contrast."""
        white_file = os.path.join(self.temp_dir.name, "white.mp4")
        create_opencv_test_mp4(
            white_file,
            width=1080,
            height=1920,
            duration_sec=2.0,
            fps=30.0,
            frame_color_init=(255, 255, 255),
            contrast_pattern=False
        )

        cover_pass, cover_errs, details = self.inspector.check_cover_thumbnail(white_file)
        assert not cover_pass
        assert any("cháy sáng" in e or "màn hình trắng xóa" in e for e in cover_errs)
        assert any("thiếu độ tương phản" in e for e in cover_errs)

    def test_unstable_cover_hold_abrupt_change(self):
        """Cover abruptly changes color at 0.5s (diff > 60.0), failing 0.75s stability hold."""
        unstable_file = os.path.join(self.temp_dir.name, "unstable_cover.mp4")
        create_opencv_test_mp4(
            unstable_file,
            width=1080,
            height=1920,
            duration_sec=2.0,
            fps=30.0,
            frame_color_init=(20, 20, 200),  # Red
            frame_color_mid=(200, 20, 20),   # Blue
            contrast_pattern=True
        )

        cover_pass, cover_errs, details = self.inspector.check_cover_thumbnail(unstable_file)
        assert not cover_pass
        assert any("Ảnh bìa không duy trì đủ 0.75s" in e for e in cover_errs)

    def test_audio_stream_absence_and_presence(self):
        # 1. Video without audio stream
        no_audio_file = os.path.join(self.temp_dir.name, "no_audio.mp4")
        create_synthetic_mp4_fast(no_audio_file, width=1080, height=1920, duration_sec=16.0, with_audio=False)
        audio_pass, audio_errs = self.inspector.check_audio_stream(no_audio_file)
        assert not audio_pass
        assert any("Video không có luồng âm thanh" in e for e in audio_errs)

        # 2. Video with synthetic audio stream
        with_audio_file = os.path.join(self.temp_dir.name, "with_audio.mp4")
        create_synthetic_mp4_fast(with_audio_file, width=1080, height=1920, duration_sec=16.0, with_audio=True)
        audio_pass, audio_errs = self.inspector.check_audio_stream(with_audio_file)
        assert audio_pass
        assert len(audio_errs) == 0

    def test_complete_valid_video_pass_100_percent(self):
        """A valid 1080x1920 vertical video with stable cover and audio passes 100%."""
        valid_file = os.path.join(self.temp_dir.name, "valid_100.mp4")
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=size=1080x1920:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=44100:duration=16.0",
            "-t", "16.0",
            "-c:v", "libx264", "-preset", "ultrafast", "-b:v", "2M",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            valid_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        valid_words = [
            {"hanzi": "苹果", "pinyin": "píng guǒ", "hidden_pinyin": "p _ _ _   g _ _", "meaning": "Quả táo"},
            {"hanzi": "香蕉", "pinyin": "xiāng jiāo", "hidden_pinyin": "x _ _ _ _   j _ _ _", "meaning": "Quả chuối"},
            {"hanzi": "西瓜", "pinyin": "xī guā", "hidden_pinyin": "x _   g _ _", "meaning": "Dưa hấu"},
            {"hanzi": "葡萄", "pinyin": "pú tao", "hidden_pinyin": "p _   t _ _", "meaning": "Quả nho"},
            {"hanzi": "草莓", "pinyin": "cǎo méi", "hidden_pinyin": "c _ _   m _ _", "meaning": "Quả dâu tây"}
        ]

        batch = {
            "id": "100",
            "topic": "Hoa Quả Hằng Ngày",
            "level": "HSK 1",
            "words": valid_words
        }

        result = self.inspector.inspect_batch(batch, valid_file)
        assert result["passed"] is True
        assert len(result["errors"]) == 0
        assert result["details"]["width"] == 1080
        assert result["details"]["height"] == 1920
        assert result["details"]["fps"] == 30.0
        assert result["details"]["duration_sec"] == 16.0
