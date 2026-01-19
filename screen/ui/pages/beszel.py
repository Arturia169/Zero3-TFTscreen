"""Beszel 监控页面模块"""
from PIL import Image, ImageDraw
from typing import Any
from ..themes import W, H, get_time_based_colors, is_night_mode, create_dynamic_background
from ..components import adjust_brightness, draw_page_header

NIGHT_DARKNESS_FACTOR = 0.3


def render(data_store: Any, fonts: dict, **kwargs) -> Image.Image:
    """渲染Beszel服务器监控页面"""
    night = is_night_mode()
    
    img = create_dynamic_background()
    draw = ImageDraw.Draw(img)
    bg_top, _, accent = get_time_based_colors()
    
    # 页面标题
    draw_page_header(draw, "服务器监控", (100, 200, 150), fonts['f_sm'])
    
    # 获取服务器数据
    clients = data_store.get("beszel_clients", [])
    
    if not clients:
        draw.text((W // 2 - 50, H // 2 - 10), "暂无服务器数据", (120, 130, 150), fonts['f_mid'])
        return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
    
    # 显示服务器列表
    y_start = 30
    card_h = 50
    
    for idx, client in enumerate(clients[:4]):
        cy = y_start + idx * (card_h + 3)
        
        # 卡片背景
        draw.rounded_rectangle([5, cy, W - 5, cy + card_h], 6,
                              fill=(bg_top[0] + 8, bg_top[1] + 10, bg_top[2] + 14))
        
        # 服务器名称
        name = client.get("name", "Unknown")[:15]
        draw.text((10, cy + 5), name, (200, 210, 225), fonts['f_sm'])
        
        # CPU 和内存使用率
        cpu = client.get("cpu", 0)
        mem = client.get("mem", 0)
        
        cpu_color = (255, 100, 100) if cpu > 80 else (255, 200, 100) if cpu > 60 else (100, 200, 150)
        mem_color = (255, 100, 100) if mem > 80 else (255, 200, 100) if mem > 60 else (100, 200, 150)
        
        draw.text((10, cy + 25), f"CPU: {cpu}%", cpu_color, fonts['f_tiny'])
        draw.text((80, cy + 25), f"MEM: {mem}%", mem_color, fonts['f_tiny'])
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
