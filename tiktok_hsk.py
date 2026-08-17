from manim import *
import os
import sys

# Project root in path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.audio_generator import ensure_bell_sound, ensure_tick_sound, generate_chinese_voice
from src.pinyin_utils import prepare_word_tuple

# Cấu hình video dọc TikTok (9:16 - 1080x1920)
config.pixel_width = 1080
config.pixel_height = 1920
config.frame_width = 9.0
config.frame_height = 16.0

CHINESE_FONT = "Arial Unicode MS"
VIETNAMESE_FONT = "Arial"

class HSKQuiz(Scene):
    def construct(self):
        # Đảm bảo các file âm thanh chuẩn (không lẫn tạp âm)
        ensure_bell_sound()
        ensure_tick_sound()

        # Danh sách chuẩn 5 từ vựng / 1 video
        raw_words = [
            ("苹果", "píng guǒ", "Quả táo"),
            ("米饭", "mǐ fàn", "Cơm"),
            ("面包", "miàn bāo", "Bánh mì"),
            ("喝水", "hē shuǐ", "Uống nước"),
            ("吃饭", "chī fàn", "Ăn cơm")
        ]

        words = []
        for item in raw_words:
            hz, py, mean = item
            h, fp, hp = prepare_word_tuple(hz, py)
            voice_path = generate_chinese_voice(hz)
            words.append({
                "hanzi": h,
                "pinyin": fp,
                "hidden_pinyin": hp,
                "meaning": mean,
                "voice": voice_path
            })

        total_words = len(words)
        topic_title = "HSK 1 • ĐỒ ĂN & THỨC UỐNG"

        # 1. Background Image
        bg_path = "assets/images/background.jpg"
        if os.path.exists(bg_path):
            bg_image = ImageMobject(bg_path)
            bg_image.set_height(config.frame_height)
            bg_image.set_width(config.frame_width)
            self.add(bg_image)
            
        dark_overlay = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color="#030712",
            fill_opacity=0.45,
            stroke_width=0
        )
        self.add(dark_overlay)

        # 2. Top Header Pill
        pill_text = Text(
            topic_title.upper(),
            font=VIETNAMESE_FONT,
            font_size=24,
            color="#082f49",
            weight=BOLD
        )
        pill_bg = RoundedRectangle(
            corner_radius=0.35,
            width=max(pill_text.width + 0.8, 3.6),
            height=0.68,
            fill_color="#38bdf8",
            fill_opacity=0.98,
            stroke_color="#7dd3fc",
            stroke_width=1.5
        ).move_to(UP * 6.7)
        pill_text.move_to(pill_bg.get_center())
        header_pill = VGroup(pill_bg, pill_text)

        # 3. Top Mode Box: "Bạn thuộc Pinyin chưa?"
        mode_card = RoundedRectangle(
            corner_radius=0.25,
            width=4.8,
            height=0.9,
            fill_color="#0b0f19",
            fill_opacity=0.88,
            stroke_color="#1e293b",
            stroke_width=1.5
        ).next_to(pill_bg, DOWN, buff=0.22)
        
        mode_title = Text(
            "Bạn thuộc Pinyin chưa?",
            font=VIETNAMESE_FONT,
            font_size=26,
            color="#fbbf24",
            weight=BOLD
        ).move_to(mode_card.get_center())
        
        header_mode = VGroup(mode_card, mode_title)
        self.play(FadeIn(header_pill, shift=DOWN*0.3), FadeIn(header_mode, shift=DOWN*0.3), run_time=0.6)

        # 4. Bottom Footer Floating Card: Logo + "lelehoctiengtrung"
        footer_card = RoundedRectangle(
            corner_radius=0.3,
            width=7.4,
            height=1.25,
            fill_color="#090d16",
            fill_opacity=0.88,
            stroke_color="#1e293b",
            stroke_width=1.5
        ).move_to(DOWN * 6.3)

        avatar_path = "assets/images/logo.png"
        if os.path.exists(avatar_path):
            avatar_img = ImageMobject(avatar_path).set_height(0.85)
            avatar_bg = RoundedRectangle(corner_radius=0.2, width=0.9, height=0.9, fill_color="#0284c7", fill_opacity=0.3, stroke_width=0)
            avatar_group = Group(avatar_bg, avatar_img).move_to(footer_card.get_left() + RIGHT * 0.75)
        else:
            avatar_group = Dot(radius=0.4, color=BLUE_D).move_to(footer_card.get_left() + RIGHT * 0.75)

        footer_title = Text("lelehoctiengtrung", font="sans-serif", font_size=32, color=WHITE, weight=BOLD)
        footer_title.next_to(avatar_group, RIGHT, buff=0.35)

        footer_base = Group(footer_card, avatar_group, footer_title)
        self.play(FadeIn(footer_base, shift=UP*0.3), run_time=0.5)

        # 5. Words Loop
        for idx, w in enumerate(words, start=1):
            hanzi = w["hanzi"]
            pinyin_full = w["pinyin"]
            hidden_py = w["hidden_pinyin"]
            meaning = w["meaning"]
            voice_file = w["voice"]

            # Word counter
            counter_text = Text(f"Từ {idx}/{total_words}", font=VIETNAMESE_FONT, font_size=26, color="#94a3b8", weight=SEMIBOLD)
            counter_text.move_to(footer_card.get_right() + LEFT * 0.9)
            self.play(FadeIn(counter_text, run_time=0.2))

            # Main Question Card
            center_card = RoundedRectangle(
                corner_radius=0.45,
                width=7.4,
                height=6.6,
                fill_color="#090d16",
                fill_opacity=0.88,
                stroke_color="#1e293b",
                stroke_width=1.5
            ).move_to(UP * 0.3)

            # 1. Chữ tiếng Trung
            hz_text = Text(
                hanzi,
                font=CHINESE_FONT,
                font_size=125,
                color=WHITE,
                weight=BOLD
            ).move_to(center_card.get_top() + DOWN * 1.3)
            
            # 2. Nghĩa tiếng Việt
            meaning_text = Text(
                f"({meaning})",
                font=VIETNAMESE_FONT,
                font_size=40,
                color="#94a3b8",
                weight=SEMIBOLD
            ).next_to(hz_text, DOWN, buff=0.28)

            # 3. Khu vực chạy Pinyin (Ẩn, hiện chữ cái đầu mỗi từ: p _ _ _   g _ _)
            hidden_text = Text(
                hidden_py,
                font="sans-serif",
                font_size=68,
                color="#facc15",
                weight=BOLD
            ).next_to(meaning_text, DOWN, buff=0.6)

            # 4. Countdown 5 giây
            time_label = Text("TIME", font="sans-serif", font_size=30, color="#94a3b8", weight=BOLD)
            timer_num = Text("5", font="sans-serif", font_size=54, color=WHITE, weight=BOLD)
            timer_group = VGroup(time_label, timer_num).arrange(RIGHT, buff=0.25).next_to(hidden_text, DOWN, buff=0.6)

            # Progress Bar Track
            bar_width = 5.4
            bar_track = RoundedRectangle(
                corner_radius=0.08,
                width=bar_width,
                height=0.16,
                fill_color="#1e293b",
                fill_opacity=0.8,
                stroke_width=0
            ).next_to(timer_group, DOWN, buff=0.35)

            active_bar = RoundedRectangle(
                corner_radius=0.08,
                width=bar_width,
                height=0.16,
                fill_color="#38bdf8",
                fill_opacity=1.0,
                stroke_width=0
            ).move_to(bar_track.get_center())

            quiz_mobjects = VGroup(center_card, hz_text, meaning_text, hidden_text, timer_group, bar_track, active_bar)
            self.play(FadeIn(quiz_mobjects, shift=UP*0.2), run_time=0.4)

            # 5s countdown với âm thanh tik thuần túy
            tick_file = "assets/audio/tick.mp3"
            total_seconds = 5
            for s in range(total_seconds, 0, -1):
                if os.path.exists(tick_file):
                    try:
                        self.add_sound(tick_file)
                    except Exception:
                        pass
                
                fraction_left = (s - 1) / total_seconds
                new_bar_width = max(bar_width * fraction_left, 0.01)
                
                new_active_bar = RoundedRectangle(
                    corner_radius=0.08,
                    width=new_bar_width,
                    height=0.16,
                    fill_color="#38bdf8" if s > 2 else "#f43f5e",
                    fill_opacity=1.0 if s > 1 else 0.0,
                    stroke_width=0
                ).move_to(bar_track.get_center()).align_to(bar_track, LEFT)
                
                display_num = str(s - 1) if s > 1 else "0"
                new_timer_num = Text(display_num, font="sans-serif", font_size=54, color=WHITE if s > 2 else "#f43f5e", weight=BOLD)
                new_timer_num.move_to(timer_num.get_center())

                self.play(
                    Transform(active_bar, new_active_bar),
                    Transform(timer_num, new_timer_num),
                    run_time=0.9,
                    rate_func=linear
                )
                self.wait(0.1)

            # HẾT 5s: Chuông thuần túy & Giọng đọc tiếng Trung chuẩn
            bell_file = "assets/audio/ding.mp3" if os.path.exists("assets/audio/ding.mp3") else "assets/audio/bell.mp3"
            if os.path.exists(bell_file):
                try:
                    self.add_sound(bell_file)
                except Exception:
                    pass
            
            if voice_file and os.path.exists(voice_file):
                try:
                    self.add_sound(voice_file)
                except Exception:
                    pass

            self.play(FadeOut(timer_group), FadeOut(bar_track), FadeOut(active_bar), run_time=0.15)

            # Hiện Pinyin đầy đủ
            answer_pinyin = Text(
                pinyin_full,
                font="sans-serif",
                font_size=75,
                color="#38bdf8",
                weight=BOLD
            ).move_to(hidden_text.get_center())

            self.play(
                Transform(hidden_text, answer_pinyin),
                run_time=0.45
            )

            # Giữ 2 giây để nghe và đọc
            self.wait(2.0)

            # Clear card
            self.play(
                FadeOut(center_card),
                FadeOut(hz_text),
                FadeOut(meaning_text),
                FadeOut(hidden_text),
                FadeOut(counter_text),
                run_time=0.35
            )

        # End Screen CTA - Gọn gàng trong khung
        end_card = RoundedRectangle(
            corner_radius=0.45,
            width=7.6,
            height=5.2,
            fill_color="#090d16",
            fill_opacity=0.94,
            stroke_color="#38bdf8",
            stroke_width=2.0
        ).move_to(UP * 0.3)

        end_title = Text("BẠN ĐOÁN ĐÚNG MẤY CÂU?", font=VIETNAMESE_FONT, font_size=34, color="#fbbf24", weight=BOLD)
        end_sub1 = Text("Comment số điểm bên dưới nhé! 👇", font=VIETNAMESE_FONT, font_size=25, color=WHITE)
        end_sub2 = Text("Follow kênh lelehoctiengtrung", font=VIETNAMESE_FONT, font_size=25, color="#38bdf8", weight=BOLD)
        end_sub3 = Text("để luyện tập mỗi ngày! ✨", font=VIETNAMESE_FONT, font_size=24, color="#cbd5e1")
        
        end_group = VGroup(end_title, end_sub1, end_sub2, end_sub3).arrange(DOWN, buff=0.28)
        if end_group.width > 6.8:
            end_group.scale_to_fit_width(6.8)
        end_group.move_to(end_card.get_center())
        
        self.play(FadeIn(end_card), FadeIn(end_group), run_time=0.5)
        self.wait(2.5)
        self.play(FadeOut(end_card), FadeOut(end_group), FadeOut(header_pill), FadeOut(header_mode), FadeOut(footer_base), run_time=0.5)

if __name__ == "__main__":
    pass
