"""UI 主题和颜色管理模块"""
from datetime import datetime
from typing import Tuple
from PIL import Image, ImageDraw

# 显示尺寸常量
W, H = 320, 240

# UI 常量
UI_HEADER_HEIGHT = 20
UI_FOOTER_HEIGHT = 16
UI_PADDING = 6
UI_CARD_RADIUS = 4
UI_CHAR_WIDTH_CN = 10
UI_CHAR_WIDTH_EN = 6


def get_time_based_colors() -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
    """根据时间返回动态色调 (背景主色, 背景副色, 装饰色)"""
    hour = datetime.now().hour
    
    if 5 <= hour < 8:  # 清晨 - 淡橙暖色
        return (22, 18, 28), (28, 22, 18), (80, 60, 40)
    elif 8 <= hour < 12:  # 上午 - 清新蓝绿
        return (15, 20, 28), (18, 25, 32), (40, 70, 80)
    elif 12 <= hour < 17:  # 下午 - 明亮蓝
        return (16, 22, 32), (20, 26, 38), (50, 80, 100)
    elif 17 <= hour < 20:  # 傍晚 - 暖橙紫
        return (25, 18, 25), (30, 20, 28), (90, 60, 70)
    elif 20 <= hour < 23:  # 夜晚 - 深蓝紫
        return (18, 16, 28), (22, 18, 35), (60, 50, 90)
    else:  # 深夜 - 深邃蓝黑
        return (12, 14, 22), (15, 16, 26), (40, 45, 70)


def create_dynamic_background(width: int = W, height: int = H) -> Image.Image:
    """创建带时间动态色调的背景"""
    bg_top, bg_bottom, accent = get_time_based_colors()
    
    img = Image.new("RGB", (width, height), bg_top)
    draw = ImageDraw.Draw(img)
    
    # 垂直渐变
    for y in range(height):
        ratio = y / height
        r = int(bg_top[0] * (1 - ratio) + bg_bottom[0] * ratio)
        g = int(bg_top[1] * (1 - ratio) + bg_bottom[1] * ratio)
        b = int(bg_top[2] * (1 - ratio) + bg_bottom[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return img


def is_night_mode(start_hour: int = 1, start_minute: int = 30, 
                  end_hour: int = 8, end_minute: int = 0) -> bool:
    """判断是否为夜间模式"""
    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute
    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute
    return start_minutes <= current_minutes < end_minutes
