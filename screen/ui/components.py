"""UI 公共组件模块"""
from typing import List, Tuple
from PIL import ImageDraw, ImageFont, ImageEnhance, Image
from .themes import (
    W, H, UI_HEADER_HEIGHT, UI_FOOTER_HEIGHT, UI_PADDING, 
    UI_CARD_RADIUS, UI_CHAR_WIDTH_CN, UI_CHAR_WIDTH_EN,
    get_time_based_colors
)


def calc_text_width(text: str) -> int:
    """计算文本像素宽度（中文约10px，英文约6px）"""
    return sum(UI_CHAR_WIDTH_CN if ord(c) > 127 else UI_CHAR_WIDTH_EN for c in text)


def truncate_text(text: str, max_width: int, ellipsis: str = "..") -> str:
    """按像素宽度截断文字"""
    if calc_text_width(text) <= max_width:
        return text
    
    ellipsis_w = calc_text_width(ellipsis)
    result = ""
    current_w = 0
    
    for c in text:
        char_w = UI_CHAR_WIDTH_CN if ord(c) > 127 else UI_CHAR_WIDTH_EN
        if current_w + char_w + ellipsis_w > max_width:
            return result + ellipsis
        result += c
        current_w += char_w
    
    return result


def draw_centered_text(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, 
                       y: int, color: Tuple[int, int, int]) -> None:
    """绘制居中文本"""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (W - text_width) // 2
    draw.text((x, y), text, fill=color, font=font)


def draw_page_header(draw: ImageDraw.Draw, title: str, accent_color: Tuple[int, int, int],
                     font, right_text: str = None, height: int = UI_HEADER_HEIGHT) -> None:
    """绘制页面标题栏"""
    bg_top, _, _ = get_time_based_colors()
    
    # 标题栏背景
    draw.rectangle([0, 0, W, height], fill=(bg_top[0] + 10, bg_top[1] + 12, bg_top[2] + 18))
    # 底部强调线
    draw.rectangle([0, height - 2, W, height], fill=accent_color)
    
    # 标题文字
    draw.text((UI_PADDING + 2, (height - 12) // 2), title, (220, 230, 245), font)
    
    # 右侧文字（如时间）
    if right_text:
        right_w = calc_text_width(right_text)
        draw.text((W - right_w - UI_PADDING - 2, (height - 10) // 2), right_text, (120, 140, 170), font)


def draw_status_bar(draw: ImageDraw.Draw, items: List[Tuple[str, Tuple[int, int, int]]],
                    font, y: int = None) -> None:
    """绘制底部状态栏"""
    if y is None:
        y = H - UI_FOOTER_HEIGHT
    
    bg_top, _, accent = get_time_based_colors()
    
    # 背景
    draw.rectangle([0, y, W, H], fill=(bg_top[0] + 5, bg_top[1] + 6, bg_top[2] + 8))
    draw.line([0, y, W, y], fill=(accent[0] + 20, accent[1] + 30, accent[2] + 40))
    
    # 均分显示各项
    if not items:
        return
    
    section_w = W // len(items)
    text_y = y + (UI_FOOTER_HEIGHT - 10) // 2
    
    for i, (text, color) in enumerate(items):
        x = i * section_w + UI_PADDING
        draw.text((x, text_y), text, color, font)


def draw_card(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int,
              fill: Tuple[int, int, int] = None, outline: Tuple[int, int, int] = None,
              radius: int = UI_CARD_RADIUS) -> None:
    """绘制圆角卡片"""
    bg_top, _, _ = get_time_based_colors()
    if fill is None:
        fill = (bg_top[0] + 8, bg_top[1] + 10, bg_top[2] + 14)
    
    draw.rounded_rectangle([x, y, x + w, y + h], radius, fill=fill, outline=outline)


def adjust_brightness(img: Image.Image, factor: float) -> Image.Image:
    """调整图像亮度"""
    return ImageEnhance.Brightness(img).enhance(factor)
