"""Worker 模块包

提供所有后台工作线程
"""
from typing import List, Any
from .base import BaseWorker


def create_all_workers(data_store: Any, config: Any, logger=None) -> List[BaseWorker]:
    """
    创建所有 Worker 实例
    
    Args:
        data_store: 数据存储对象
        config: 配置对象
        logger: 日志记录器
    
    Returns:
        Worker 实例列表
    """
    # 延迟导入避免循环依赖
    from .weather import WeatherWorker
    from .system import SystemWorker
    from .crypto import CryptoWorker
    from .tracking import TrackingWorker
    from .bilibili import BilibiliWorker
    from .beszel import BeszelWorker
    from .telegram import TelegramWorker
    
    # 从配置读取更新间隔
    weather_interval = config.get("weather.update_interval", 1800) if config else 1800
    system_interval = config.get("system.update_interval", 2) if config else 2
    crypto_interval = config.get("crypto.update_interval", 15) if config else 15
    
    workers = [
        WeatherWorker(data_store, weather_interval, config, logger),
        SystemWorker(data_store, system_interval, logger),
        CryptoWorker(data_store, crypto_interval, config, logger),
        TrackingWorker(data_store, 60, config, logger),
        BilibiliWorker(data_store, 60, config, logger),
        BeszelWorker(data_store, 60, config, logger),
        TelegramWorker(data_store, 60, config, logger),
    ]
    
    return workers
