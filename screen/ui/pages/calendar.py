"""日历页面模块"""
from PIL import Image, ImageDraw
from datetime import datetime, timedelta
from typing import Any
from ..themes import W, H, get_time_based_colors, is_night_mode, create_dynamic_background
from ..components import adjust_brightness

NIGHT_DARKNESS_FACTOR = 0.3
TARGET_DATE = datetime(2026, 2, 17)
TARGET_NAME = "CNY 2026"


def render(data_store: Any, fonts: dict, **kwargs) -> Image.Image:
    """渲染日历倒数日页面"""
    night = is_night_mode()
    
    img = create_dynamic_background()
    draw = ImageDraw.Draw(img)
    
    now = datetime.now()
    days_left = (TARGET_DATE - now).days
    
    # 居中显示倒数日
    title_text = TARGET_NAME
    title_bbox = draw.textbbox((0, 0), title_text, fonts['f_big'])
    title_w = title_bbox[2] - title_bbox[0]
    title_x = (W - title_w) // 2
    draw.text((title_x, 60), title_text, (255, 200, 100), fonts['f_big'])
    
    # 显示剩余天数
    days_text = f"{days_left} 天"
    days_bbox = draw.textbbox((0, 0), days_text, fonts['f_big'])
    days_w = days_bbox[2] - days_bbox[0]
    days_x = (W - days_w) // 2
    draw.text((days_x, 120), days_text, (100, 200, 255), fonts['f_big'])
    
    # 显示当前日期
    date_text = now.strftime("%Y年%m月%d日")
    date_bbox = draw.textbbox((0, 0), date_text, fonts['f_mid'])
    date_w = date_bbox[2] - date_bbox[0]
    date_x = (W - date_w) // 2
    draw.text((date_x, 180), date_text, (150, 160, 180), fonts['f_mid'])
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
