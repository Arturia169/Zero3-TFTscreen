"""页面模块包

提供所有页面的渲染函数
"""
from typing import List, Callable
from PIL import Image


def get_all_pages() -> List[Callable]:
    """
    获取所有页面渲染函数列表
    
    Returns:
        页面渲染函数列表
    """
    # 延迟导入避免循环依赖
    from . import clock, crypto, calendar, tracking, bilibili, beszel, telegram
    
    return [
        clock.render,
        tracking.render,
        bilibili.render,
        crypto.render,
        calendar.render,
        beszel.render,
        telegram.render
    ]
