"""Beszel 监控 Worker（简化版本）"""
from .base import BaseWorker


class BeszelWorker(BaseWorker):
    """Beszel 服务器监控线程"""
    
    def __init__(self, data_store, interval, config=None, logger=None):
        super().__init__(data_store, interval, logger)
        self.config = config
    
    def update(self) -> None:
        """更新Beszel监控数据"""
        try:
            self._log('debug', "Updating beszel data...")
            # 完整实现需要从 main.py 中提取
        except Exception as e:
            self._log('error', f"Failed to update beszel: {e}")
