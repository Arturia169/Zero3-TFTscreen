"""Telegram 消息页面模块"""
from PIL import Image, ImageDraw
from typing import Any
from ..themes import W, H, get_time_based_colors, is_night_mode, create_dynamic_background
from ..components import adjust_brightness, draw_page_header

NIGHT_DARKNESS_FACTOR = 0.3


def render(data_store: Any, fonts: dict, **kwargs) -> Image.Image:
    """渲染Telegram消息页面"""
    night = is_night_mode()
    
    img = create_dynamic_background()
    draw = ImageDraw.Draw(img)
    bg_top, _, accent = get_time_based_colors()
    
    # 页面标题
    draw_page_header(draw, "Telegram", (100, 180, 255), fonts['f_sm'])
    
    # 获取消息数据
    messages = data_store.get("telegram_messages", [])
    
    if not messages:
        draw.text((W // 2 - 40, H // 2 - 10), "暂无消息", (120, 130, 150), fonts['f_mid'])
        return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
    
    # 显示最新的3条消息
    y_start = 30
    card_h = 65
    
    for idx, msg in enumerate(messages[:3]):
        cy = y_start + idx * (card_h + 5)
        
        # 卡片背景
        draw.rounded_rectangle([5, cy, W - 5, cy + card_h], 6,
                              fill=(bg_top[0] + 8, bg_top[1] + 10, bg_top[2] + 14))
        
        # 频道名
        channel = msg.get("channel", "Unknown")[:15]
        draw.text((10, cy + 5), channel, (100, 180, 255), fonts['f_sm'])
        
        # 消息内容（截断）
        text = msg.get("text", "")[:40]
        if len(msg.get("text", "")) > 40:
            text += "..."
        draw.text((10, cy + 25), text, (180, 190, 210), fonts['f_tiny'])
        
        # 时间
        time_str = msg.get("time", "")
        draw.text((10, cy + 45), time_str, (120, 130, 150), fonts['f_tiny'])
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
