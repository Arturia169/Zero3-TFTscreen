"""加密货币页面模块"""
from PIL import Image, ImageDraw
from typing import Any
from ..themes import W, H, get_time_based_colors, is_night_mode, create_dynamic_background
from ..components import adjust_brightness

NIGHT_DARKNESS_FACTOR = 0.3


def render(data_store: Any, fonts: dict, **kwargs) -> Image.Image:
    """渲染加密货币监控页面"""
    night = is_night_mode()
    
    # 使用动态背景
    img = create_dynamic_background()
    draw = ImageDraw.Draw(img)
    bg_top, _, accent = get_time_based_colors()
    
    # 颜色定义
    up_color = (38, 166, 91)
    down_color = (234, 57, 67)
    text_dim = (100, 110, 130)
    text_bright = (200, 210, 225)
    
    # ===== 顶部资产栏 =====
    header_h = 24
    draw.rectangle([0, 0, W, header_h], fill=(bg_top[0] + 8, bg_top[1] + 10, bg_top[2] + 12))
    
    # 资产信息
    draw.text((4, 2), "ASSETS", text_dim, fonts['f_tiny'])
    asset_str = data_store.get('bybit_asset', 'Loading...')
    draw.text((50, 2), asset_str, (255, 230, 100), fonts['f_tiny'])
    
    # 资产变化
    asset_history = data_store.get("bybit_asset_history", [])
    if len(asset_history) >= 2:
        first_val = asset_history[0][1]
        last_val = asset_history[-1][1]
        if first_val > 0:
            asset_change = ((last_val - first_val) / first_val) * 100
            change_color = up_color if asset_change >= 0 else down_color
            draw.text((130, 2), f"{asset_change:+.1f}%", change_color, fonts['f_tiny'])
    
    draw.line([0, header_h, W, header_h], fill=(40, 50, 65))
    
    # ===== 三个币种显示区域 =====
    crypto_data = data_store.get("crypto", [])
    content_y = header_h + 2
    content_h = H - header_h - 4
    col_w = W // 3
    
    coin_names = ["BTC", "ETH", "DOGE"]
    
    for col_idx, coin_name in enumerate(coin_names):
        cx = col_idx * col_w
        
        # 找到对应币种数据
        coin_data = None
        for c in crypto_data:
            if c.get("name") == coin_name:
                coin_data = c
                break
        
        # 币种标题栏
        title_h = 28
        draw.rectangle([cx, content_y, cx + col_w - 1, content_y + title_h], fill=(20, 25, 32))
        
        if coin_data:
            price = coin_data.get("price", "0")
            change = coin_data.get("change", 0)
            is_up = change >= 0
            color = up_color if is_up else down_color
            
            # 币种名
            draw.text((cx + 3, content_y + 2), coin_name, text_bright, fonts['f_tiny'])
            
            # 价格
            price_str = f"${price}" if float(price) >= 1 else f"${float(price):.4f}"
            if len(price_str) > 10:
                price_str = f"${float(price):.0f}"
            draw.text((cx + 3, content_y + 14), price_str, color, fonts['f_tiny'])
            
            # 涨跌幅
            change_str = f"{change:+.1f}%"
            draw.text((cx + col_w - 36, content_y + 8), change_str, color, fonts['f_tiny'])
        else:
            draw.text((cx + 3, content_y + 8), coin_name, text_dim, fonts['f_tiny'])
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
