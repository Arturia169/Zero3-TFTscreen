"""物流追踪页面模块"""
from PIL import Image, ImageDraw
from typing import Any
from ..themes import W, H, get_time_based_colors, is_night_mode, create_dynamic_background
from ..components import adjust_brightness, draw_page_header

NIGHT_DARKNESS_FACTOR = 0.3


def render(data_store: Any, fonts: dict, **kwargs) -> Image.Image:
    """渲染物流追踪页面"""
    night = is_night_mode()
    
    img = create_dynamic_background()
    draw = ImageDraw.Draw(img)
    bg_top, _, accent = get_time_based_colors()
    
    # 页面标题
    draw_page_header(draw, "物流追踪", (100, 180, 255), fonts['f_sm'])
    
    # 获取包裹数据
    packages = data_store.get("tracking_packages", [])
    
    if not packages:
        # 无包裹提示
        draw.text((W // 2 - 50, H // 2 - 10), "暂无物流信息", (120, 130, 150), fonts['f_mid'])
        return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
    
    # 显示前2个包裹
    y_start = 30
    card_h = 100
    
    for idx, pkg in enumerate(packages[:2]):
        cy = y_start + idx * (card_h + 5)
        
        # 卡片背景
        draw.rounded_rectangle([5, cy, W - 5, cy + card_h], 6, 
                              fill=(bg_top[0] + 8, bg_top[1] + 10, bg_top[2] + 14))
        
        # 快递公司和单号
        company = pkg.get("company", "未知")
        number = pkg.get("number", "")
        draw.text((10, cy + 5), f"{company}", (200, 210, 225), fonts['f_sm'])
        draw.text((10, cy + 20), f"{number[:15]}...", (120, 130, 150), fonts['f_tiny'])
        
        # 最新状态
        tracks = pkg.get("tracks", [])
        if tracks:
            latest = tracks[0]
            status = latest.get("context", "")[:30]
            draw.text((10, cy + 40), status, (180, 190, 210), fonts['f_tiny'])
    
    # 显示包裹总数
    if len(packages) > 2:
        draw.text((W - 60, H - 20), f"+{len(packages) - 2} 更多", (100, 120, 150), fonts['f_tiny'])
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
