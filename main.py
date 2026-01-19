#!/usr/bin/env python3
"""
香橙派智能屏幕 - 主入口（模块化版本）

这是重构后的精简版 main.py，所有功能已模块化
"""
import os
import sys
import time
import threading

# 添加项目根目录到 Python 路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# 导入新模块
from screen.utils.logger import setup_logger
from screen.core.config import load_config
from screen.core.data_store import DataStore
from screen.core.display import DisplayDriver
from screen.workers import create_all_workers
from screen.ui.pages import get_all_pages
from screen.web.api import start_web_server

# 初始化日志
logger = setup_logger("main", log_file="/tmp/rili_screen.log")

# 全局变量（用于页面渲染）
# TODO: 这些应该通过参数传递，而不是全局变量
info = None  # DataStore 实例
f_tiny = None
f_sm = None
f_mid = None
f_big = None
f_renix_big = None


def load_fonts():
    """加载字体"""
    from PIL import ImageFont
    
    global f_tiny, f_sm, f_mid, f_big, f_renix_big
    
    # 尝试多个字体路径
    font_paths = [
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        os.path.join(BASE_DIR, "fonts", "wqy-zenhei.ttc"),
    ]
    
    font_path = None
    for path in font_paths:
        if os.path.exists(path):
            font_path = path
            break
    
    if not font_path:
        logger.warning("Chinese font not found, using default")
        f_tiny = ImageFont.load_default()
        f_sm = ImageFont.load_default()
        f_mid = ImageFont.load_default()
        f_big = ImageFont.load_default()
        f_renix_big = ImageFont.load_default()
    else:
        try:
            f_tiny = ImageFont.truetype(font_path, 10)
            f_sm = ImageFont.truetype(font_path, 14)
            f_mid = ImageFont.truetype(font_path, 18)
            f_big = ImageFont.truetype(font_path, 32)
            f_renix_big = ImageFont.truetype(font_path, 48)
            logger.info(f"Fonts loaded from {font_path}")
        except Exception as e:
            logger.error(f"Failed to load fonts: {e}")
            f_tiny = f_sm = f_mid = f_big = f_renix_big = ImageFont.load_default()


def main():
    """主函数"""
    global info
    
    logger.info("=" * 50)
    logger.info("启动香橙派智能屏幕系统（模块化版本）")
    logger.info("=" * 50)
    
    # 1. 加载配置
    config = load_config()
    logger.info("配置加载完成")
    
    # 2. 初始化数据存储
    info = DataStore()
    logger.info("数据存储初始化完成")
    
    # 3. 加载字体
    load_fonts()
    
    # 4. 初始化显示驱动
    display = DisplayDriver(config, logger)
    if not display.init_display():
        logger.error("显示器初始化失败，退出")
        return
    logger.info("显示器初始化完成")
    
    # 5. 启动所有 Worker 线程
    workers = create_all_workers(info, config, logger)
    for worker in workers:
        worker.start()
    logger.info(f"已启动 {len(workers)} 个后台工作线程")
    
    # 6. 启动 Web 服务器
    web_port = config.get("web.port", 8080) if config else 8080
    web_thread = threading.Thread(
        target=start_web_server,
        args=(info, config, logger, web_port),
        daemon=True
    )
    web_thread.start()
    logger.info(f"Web 管理界面已启动: http://0.0.0.0:{web_port}")
    
    # 7. 获取所有页面
    pages = get_all_pages()
    logger.info(f"已加载 {len(pages)} 个页面模块")
    
    # 8. 主显示循环
    logger.info("进入主显示循环...")
    
    current_page = 0
    last_update = 0
    UPDATE_INTERVAL = 1.0  # 每秒更新一次
    
    # 准备字体字典
    fonts = {
        'f_tiny': f_tiny,
        'f_sm': f_sm,
        'f_mid': f_mid,
        'f_big': f_big,
        'f_renix_big': f_renix_big
    }
    
    try:
        while True:
            current_time = time.time()
            
            # 每秒更新一次显示
            if current_time - last_update >= UPDATE_INTERVAL:
                try:
                    # 渲染当前页面
                    page_func = pages[current_page % len(pages)]
                    img = page_func(info, fonts, base_dir=BASE_DIR, logger=logger)
                    
                    # 显示图像
                    display.display_image(img)
                    
                    last_update = current_time
                except Exception as e:
                    logger.error(f"页面渲染失败: {e}")
            
            # 页面自动切换（每10秒）
            if int(current_time) % 10 == 0:
                current_page = (current_page + 1) % len(pages)
                time.sleep(1)  # 避免重复切换
            
            time.sleep(0.1)  # 减少 CPU 占用
            
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在退出...")
    except Exception as e:
        logger.error(f"主循环异常: {e}", exc_info=True)
    finally:
        # 清理资源
        for worker in workers:
            worker.stop()
        display.close()
        logger.info("系统已退出")


if __name__ == "__main__":
    main()
