import os
import pytest
from PIL import ImageFont

def test_font_assets_exist_and_loadable():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonts_dir = os.path.join(base_dir, "assets", "fonts")
    
    bold_font_path = os.path.join(fonts_dir, "NotoSansSC-Bold.otf")
    regular_font_path = os.path.join(fonts_dir, "NotoSansSC.ttf")
    
    assert os.path.exists(bold_font_path), "NotoSansSC-Bold.otf must exist"
    assert os.path.exists(regular_font_path), "NotoSansSC.ttf must exist"
    
    # Must not be corrupted 105-byte 404 text
    assert os.path.getsize(bold_font_path) > 10000, "NotoSansSC-Bold.otf must not be 105-byte text error"
    assert os.path.getsize(regular_font_path) > 10000, "NotoSansSC.ttf must be a valid binary font"
    
    # Verify PIL ImageFont can render glyphs
    font1 = ImageFont.truetype(bold_font_path, 24)
    font2 = ImageFont.truetype(regular_font_path, 24)
    
    assert font1 is not None
    assert font2 is not None
