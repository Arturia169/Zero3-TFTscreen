"""日志配置模块"""
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_logger(
    name: str = __name__,
    level: int = logging.INFO,
    log_file: Optional[str] = "/tmp/rili_screen.log",
    max_bytes: int = 5 * 1024 * 1024,  # 5MB
    backup_count: int = 2
) -> logging.Logger:
    """
    配置并返回一个日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        log_file: 日志文件路径，None 则只输出到控制台
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数量
    
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件输出（带轮转）
    if log_file:
        try:
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"无法创建日志文件 {log_file}: {e}")
    
    return logger


# 创建默认 logger
logger = setup_logger()
