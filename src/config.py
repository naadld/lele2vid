import os
from dataclasses import dataclass, field
from typing import List

@dataclass
class AppConfig:
    # Spreadsheet Settings
    spreadsheet_id: str = "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0"
    sheet_tab_name: str = "pinyin"
    
    # Credential Paths
    creds_paths: List[str] = field(default_factory=lambda: [
        "/media/vpsg16gb/Workspace/lelehoctiengtrung_pinyin/configs/service_account.json",
        "/media/vpsg16gb/Workspace/Projects/lelehoctiengtrung/Pipeline_lelehoctiengtrung/gitignore/service_account.json",
        "/media/vpsg16gb/Workspace/Projects/lelehoctiengtrung/Pipeline_lelehoctiengtrung/lele-step10-karaoke/service_account.json",
        os.path.expanduser("~/.config/gspread/service_account.json")
    ])
    
    # Video Specs (9:16 Vertical for TikTok/Shorts/Reels)
    pixel_width: int = 1080
    pixel_height: int = 1920
    frame_width: float = 9.0
    frame_height: float = 16.0
    
    # Fonts
    chinese_font: str = "Arial Unicode MS"
    latin_font: str = "sans-serif"
    
    # Timing
    countdown_seconds: int = 5
    answer_wait_seconds: float = 2.0
    transition_wait_seconds: float = 0.5
    
    # Paths
    base_dir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_audio_dir: str = os.path.join(base_dir, "assets", "audio")
    output_videos_dir: str = os.path.join(base_dir, "output", "videos")
    generated_scenes_dir: str = os.path.join(base_dir, "output", "generated_scenes")
    bell_audio_path: str = os.path.join(assets_audio_dir, "bell.mp3")

config = AppConfig()
