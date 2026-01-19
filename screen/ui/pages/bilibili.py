"""B站监控页面模块"""
from PIL import Image, ImageDraw
from datetime import datetime
from typing import Any
from ..themes import W, H, get_time_based_colors, is_night_mode, create_dynamic_background
from ..components import adjust_brightness

NIGHT_DARKNESS_FACTOR = 0.3


def render(data_store: Any, fonts: dict, **kwargs) -> Image.Image:
    """渲染B站主播监控页面"""
    night = is_night_mode()
    
    img = create_dynamic_background()
    draw = ImageDraw.Draw(img)
    bg_top, _, accent = get_time_based_colors()
    
    # ========== 顶部状态栏 ==========
    header_h = 14
    draw.rectangle([0, 0, W, header_h], fill=(bg_top[0] + 12, bg_top[1] + 13, bg_top[2] + 17))
    draw.rectangle([0, header_h - 1, W, header_h], fill=(251, 114, 153))
    
    user = data_store.get("bilibili_user", {})
    now = datetime.now()
    streamers = data_store.get("bilibili_streamers", [])
    
    # 左侧: 用户信息
    if user:
        uname = user.get("uname", "")[:5]
        level = user.get("level", 0)
        draw.text((4, 1), uname, (255, 255, 255), fonts['f_tiny'])
        lv_color = (251, 114, 153) if level >= 6 else (80, 140, 200)
        draw.text((50, 1), f"Lv{level}", lv_color, fonts['f_tiny'])
    
    # 右侧: 直播数/总数
    live_count = sum(1 for s in streamers if s.get("live_status") == 1)
    total_count = len(streamers)
    status_text = f"{live_count}/{total_count}"
    draw.text((W - 70, 1), status_text, (251, 114, 153) if live_count > 0 else (100, 105, 120), fonts['f_tiny'])
    draw.text((W - 30, 1), now.strftime("%H:%M"), (140, 145, 160), fonts['f_tiny'])
    
    # ========== 主播卡片区域 ==========
    content_y = header_h + 2
    content_h = H - header_h - 4
    
    if not streamers:
        draw.text((W // 2 - 40, H // 2 - 10), "暂无关注主播", (100, 105, 120), fonts['f_sm'])
        return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
    
    # 按直播状态排序
    sorted_streamers = sorted(streamers, key=lambda x: (x.get("live_status", 0) != 1, -x.get("online", 0)))
    
    # 2列显示，每列4个
    col_w = W // 2
    card_h = content_h // 4
    max_show = 8
    
    for idx, s in enumerate(sorted_streamers[:max_show]):
        col = idx % 2
        row = idx // 2
        
        cx = col * col_w + 2
        cy = content_y + row * card_h
        card_w = col_w - 4
        
        is_live = s.get("live_status") == 1
        alias = s.get("alias", "") or s.get("uname", "") or "主播"
        
        # 卡片背景
        if is_live:
            bg_color = (35, 25, 30)
            draw.rectangle([cx, cy, cx + card_w, cy + card_h - 2], fill=bg_color)
            draw.rectangle([cx, cy, cx + 2, cy + card_h - 2], fill=(251, 114, 153))
        else:
            bg_color = (28, 30, 38)
            draw.rectangle([cx, cy, cx + card_w, cy + card_h - 2], fill=bg_color)
            draw.rectangle([cx, cy, cx + 2, cy + card_h - 2], fill=(50, 55, 70))
        
        # 主播名
        name_display = alias[:6]
        name_color = (255, 255, 255) if is_live else (140, 145, 160)
        draw.text((cx + 5, cy + 2), name_display, name_color, fonts['f_tiny'])
        
        if is_live:
            draw.text((cx + card_w - 28, cy + 2), "LIVE", (251, 114, 153), fonts['f_tiny'])
        else:
            draw.text((cx + 5, cy + 14), "未开播", (80, 85, 100), fonts['f_tiny'])
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
