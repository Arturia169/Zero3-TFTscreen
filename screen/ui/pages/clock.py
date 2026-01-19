"""时钟页面模块 - Nixie 管风格时钟

注意：此模块是从 main.py 中提取的 draw_clock() 函数
完整迁移需要处理全局变量依赖（如字体、BASE_DIR 等）
"""
import os
from datetime import datetime
from PIL import Image, ImageDraw
from zhdate import ZhDate
from typing import Any

# 这些将来需要从配置或参数传入
W, H = 320, 240
NIGHT_DARKNESS_FACTOR = 0.3

# 全局素材缓存
NIXIE_IMAGE_CACHE = {}


def render(data_store: Any, fonts: dict, base_dir: str, logger=None) -> Image.Image:
    """
    渲染时钟页面
    
    Args:
        data_store: 数据存储对象
        fonts: 字体字典 {'f_tiny': font, 'f_sm': font, ...}
        base_dir: 项目根目录
        logger: 日志记录器
    
    Returns:
        PIL Image 对象
    """
    from ..themes import get_time_based_colors, is_night_mode
    from ..components import adjust_brightness
    
    now = datetime.now()
    night = is_night_mode()
    
    # 极深黑背景
    img = Image.new("RGB", (W, H), (5, 5, 8))
    draw = ImageDraw.Draw(img)
    
    # 获取时间色调
    bg_top, _, accent = get_time_based_colors()
    
    # ========== 1. 顶部信息栏 ==========
    header_h = 28
    
    # 顶部渐变背景
    for hy in range(header_h):
        alpha = hy / header_h
        r = int(15 * (1 - alpha) + 8 * alpha)
        g = int(18 * (1 - alpha) + 10 * alpha)
        b = int(25 * (1 - alpha) + 15 * alpha)
        draw.rectangle([0, hy, W, hy + 1], fill=(r, g, b))
    
    # 底部发光线
    draw.rectangle([0, header_h - 2, W, header_h - 1], fill=(50, 80, 120))
    draw.rectangle([0, header_h - 1, W, header_h], fill=(25, 40, 60))
    
    # 左侧：模式标识
    mode_text = "NIGHT" if night else "DAY"
    mode_color = (100, 160, 220) if night else (220, 200, 120)
    dot_color = (80, 140, 200) if night else (200, 180, 80)
    draw.ellipse([6, 10, 12, 16], fill=dot_color)
    draw.text((16, 6), mode_text, mode_color, fonts['f_tiny'])
    
    # 中间：日期 + 星期 + 农历
    month = now.month
    day = now.day
    weekdays = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    weekday = weekdays[now.weekday()]
    
    # 农历
    lunar_text = ""
    try:
        lunar = ZhDate.from_datetime(now)
        lunar_month_names = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
        lunar_day_names = ["初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
                          "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
                          "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"]
        lunar_text = f"{lunar_month_names[lunar.lunar_month - 1]}月{lunar_day_names[lunar.lunar_day - 1]}"
    except Exception:
        pass
    
    # 组合日期文本
    date_text = f"{month:02d}/{day:02d} {weekday}"
    if lunar_text:
        date_text += f" {lunar_text}"
    
    date_bbox = draw.textbbox((0, 0), date_text, fonts['f_sm'])
    date_w = date_bbox[2] - date_bbox[0]
    date_x = (W - date_w) // 2
    
    is_weekend = now.weekday() >= 5
    date_color = (255, 180, 120) if is_weekend else (220, 225, 235)
    draw.text((date_x, 8), date_text, date_color, fonts['f_sm'])
    
    # ========== 2. 加载辉光管素材图片 (带全局缓存) ==========
    global NIXIE_IMAGE_CACHE
    
    nixie_dir = os.path.join(base_dir, "辉光管素材图")
    tube_target_h = 110
    width_scale = 1.45
    
    # 如果缓存为空，则加载一次
    if not NIXIE_IMAGE_CACHE:
        if logger:
            logger.info("正在加载辉光管素材至内存缓存...")
        for d in range(10):
            try:
                img_path = f"{nixie_dir}/{d}.png"
                if os.path.exists(img_path):
                    nixie_img = Image.open(img_path).convert("RGBA")
                    ratio = tube_target_h / nixie_img.height
                    new_w = int(nixie_img.width * ratio * width_scale)
                    nixie_img = nixie_img.resize((new_w, tube_target_h), Image.Resampling.LANCZOS)
                    NIXIE_IMAGE_CACHE[str(d)] = nixie_img
            except Exception as e:
                if logger:
                    logger.warning(f"加载辉光管素材 {d}.png 失败: {e}")
    
    nixie_images = NIXIE_IMAGE_CACHE
    
    # ========== 3. 绘制时间数字 ==========
    time_str = now.strftime("%H%M")
    digits = list(time_str)
    
    if nixie_images:
        sample_img = list(nixie_images.values())[0]
        tube_w = sample_img.width
    else:
        tube_w = 75
    
    colon_w = 10
    gap = 2
    total_w = tube_w * 4 + colon_w + gap * 3
    start_x = (W - total_w) // 2
    base_y = 28
    
    curr_x = start_x
    for i, digit in enumerate(digits):
        if digit in nixie_images:
            nixie_img = nixie_images[digit]
            img.paste(nixie_img, (curr_x, base_y), nixie_img)
        else:
            draw.text((curr_x + 15, base_y + 30), digit, (255, 140, 40), fonts.get('f_renix_big', fonts['f_sm']))
        
        curr_x += tube_w + gap
        if i == 1:
            curr_x += colon_w
    
    # ========== 4. 底部信息栏 ==========
    footer_y = H - 16
    draw.rectangle([0, footer_y, W, H], fill=(bg_top[0] + 5, bg_top[1] + 6, bg_top[2] + 8))
    draw.line([0, footer_y, W, footer_y], fill=(accent[0] + 20, accent[1] + 30, accent[2] + 40))
    
    text_y = footer_y + 3
    
    # 左侧：运行时间
    uptime = data_store.get('uptime', '0天0时')
    draw.text((6, text_y), uptime, (100, 160, 140), fonts['f_tiny'])
    
    # 中间：BTC价格
    crypto_data = data_store.get('crypto', [])
    btc_price = 0
    for c in crypto_data:
        if c.get('name') == 'BTC':
            try:
                btc_price = float(c.get('price', 0))
            except:
                pass
            break
    if btc_price > 0:
        btc_str = f"BTC:{btc_price/1000:.1f}K"
        draw.text((W // 2 - 30, text_y), btc_str, (255, 200, 100), fonts['f_tiny'])
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
