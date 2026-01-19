"""Worker 线程基类"""
import time
import threading
from typing import Any, Optional


class BaseWorker:
    """后台工作线程基类"""
    
    def __init__(self, data_store: Any, interval: int, logger=None):
        """
        初始化 Worker
        
        Args:
            data_store: 数据存储对象
            interval: 更新间隔（秒）
            logger: 日志记录器
        """
        self.data_store = data_store
        self.interval = interval
        self._logger = logger
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def _log(self, level: str, message: str):
        """内部日志方法"""
        if self._logger:
            getattr(self._logger, level)(message)
    
    def start(self) -> None:
        """启动 Worker 线程"""
        if self._running:
            self._log('warning', f"{self.__class__.__name__} already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name=self.__class__.__name__)
        self._thread.start()
        self._log('info', f"{self.__class__.__name__} started")
    
    def stop(self) -> None:
        """停止 Worker 线程"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._log('info', f"{self.__class__.__name__} stopped")
    
    def _run(self) -> None:
        """Worker 主循环"""
        while self._running:
            try:
                self.update()
            except Exception as e:
                self._log('error', f"{self.__class__.__name__} update error: {e}")
            
            # 分段睡眠以便快速响应停止信号
            for _ in range(self.interval):
                if not self._running:
                    break
                time.sleep(1)
    
    def update(self) -> None:
        """
        更新数据的具体逻辑（子类实现）
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement update()")
