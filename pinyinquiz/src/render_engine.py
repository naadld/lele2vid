import os
import sys
import subprocess
import glob
import shutil
import logging
from typing import Tuple
from src.config import config
from src.audio_generator import ensure_bell_sound

logger = logging.getLogger("RenderEngine")

def render_manim_scene(
    scene_file: str,
    scene_name: str,
    quality: str = "qh",
    output_filename: str = None
) -> str:
    """
    Renders Manim scene.
    quality:
      - 'ql': Low quality (480p15) for fast preview
      - 'qm': Medium quality (720p30)
      - 'qh': High quality (1080p60) for TikTok production
    """
    ensure_bell_sound()
    os.makedirs(config.output_videos_dir, exist_ok=True)
    
    python_bin = os.path.join(os.path.dirname(sys.executable), "manim")
    if not os.path.exists(python_bin):
        python_bin = os.path.join(config.base_dir, ".venv", "bin", "manim")
    if not os.path.exists(python_bin):
        python_bin = os.path.join(os.path.dirname(config.base_dir), ".venv", "bin", "manim")
    if not os.path.exists(python_bin):
        python_bin = shutil.which("manim") or "manim"
        
    media_dir = os.path.join(config.base_dir, "output", "media")
    os.makedirs(media_dir, exist_ok=True)
    
    cmd = [
        python_bin,
        f"-{quality}",
        "--disable_caching",
        scene_file,
        scene_name,
        "--media_dir", media_dir
    ]
    
    logger.info(f"Executing Manim render: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=config.base_dir, capture_output=True, text=True)
    
    if result.returncode != 0:
        logger.error(f"Manim render failed! Error log:\n{result.stderr}")
        raise RuntimeError(f"Manim render error: {result.stderr}")
        
    # Search for rendered MP4 file
    search_pattern = os.path.join(media_dir, "videos", "**", f"{scene_name}.mp4")
    matching_files = glob.glob(search_pattern, recursive=True)
    
    if not matching_files:
        # Fallback search for any newly generated mp4 in media_dir
        all_mp4s = glob.glob(os.path.join(media_dir, "videos", "**", "*.mp4"), recursive=True)
        if all_mp4s:
            matching_files = [max(all_mp4s, key=os.path.getmtime)]
            
    if not matching_files:
        raise FileNotFoundError(f"Could not find rendered video for {scene_name} in {media_dir}")
        
    raw_video = matching_files[0]
    
    if not output_filename:
        output_filename = f"{scene_name}.mp4"
    if not output_filename.endswith(".mp4"):
        output_filename += ".mp4"
        
    final_output_path = os.path.join(config.output_videos_dir, output_filename)
    shutil.copy2(raw_video, final_output_path)
    logger.info(f"Video saved successfully to: {final_output_path}")
    return final_output_path

def render_scene_file(
    scene_file: str,
    scene_name: str,
    quality: str = "qh",
    custom_output_name: str = None
) -> Tuple[bool, str]:
    """Wrapper function returning (success, output_path)."""
    try:
        path = render_manim_scene(scene_file, scene_name, quality=quality, output_filename=custom_output_name)
        return True, path
    except Exception as e:
        logger.error(f"Render failed for {scene_name}: {e}")
        return False, ""

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        render_manim_scene(sys.argv[1], sys.argv[2])
