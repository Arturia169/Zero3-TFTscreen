"""配置文件热加载模块"""
import os
import time
import threading
from typing import Dict, List, Callable

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object


class ConfigReloader(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """配置文件热加载器"""
    
    def __init__(self, logger=None):
        if WATCHDOG_AVAILABLE:
            super().__init__()
        self._callbacks: Dict[str, List[Callable]] = {}
        self._last_modified: Dict[str, float] = {}
        self._debounce_seconds = 1.0
        self._observer = None
        self._watched_dirs = set()
        self._logger = logger
    
    def _log(self, level: str, message: str):
        """内部日志方法"""
        if self._logger:
            getattr(self._logger, level)(message)
        else:
            print(f"[{level.upper()}] {message}")
    
    def register(self, file_path: str, callback: Callable) -> None:
        """注册配置文件和回调函数"""
        abs_path = os.path.abspath(file_path)
        if abs_path not in self._callbacks:
            self._callbacks[abs_path] = []
        self._callbacks[abs_path].append(callback)
        
        # 添加目录监控
        dir_path = os.path.dirname(abs_path)
        if dir_path and dir_path not in self._watched_dirs:
            self._watched_dirs.add(dir_path)
            if self._observer and os.path.exists(dir_path):
                self._observer.schedule(self, dir_path, recursive=False)
        
        self._log('info', f"注册配置热加载: {file_path}")
    
    def on_modified(self, event):
        """文件修改事件处理"""
        if event.is_directory:
            return
        
        file_path = os.path.abspath(event.src_path)
        
        # 检查是否是我们监控的文件
        if file_path not in self._callbacks:
            return
        
        # 防抖处理
        now = time.time()
        last_time = self._last_modified.get(file_path, 0)
        if now - last_time < self._debounce_seconds:
            return
        self._last_modified[file_path] = now
        
        # 延迟执行回调（确保文件写入完成）
        def delayed_reload():
            time.sleep(0.5)
            self._log('info', f"检测到配置变更: {file_path}")
            for callback in self._callbacks.get(file_path, []):
                try:
                    callback()
                    self._log('info', f"配置重载成功: {file_path}")
                except Exception as e:
                    self._log('error', f"配置重载失败 {file_path}: {e}")
        
        threading.Thread(target=delayed_reload, daemon=True).start()
    
    def start(self) -> bool:
        """启动配置监控"""
        if not WATCHDOG_AVAILABLE:
            self._log('warning', "watchdog 库未安装，配置热加载不可用")
            return False
        
        try:
            self._observer = Observer()
            
            # 监控所有已注册的目录
            for dir_path in self._watched_dirs:
                if os.path.exists(dir_path):
                    self._observer.schedule(self, dir_path, recursive=False)
            
            self._observer.start()
            self._log('info', f"配置热加载已启动，监控 {len(self._watched_dirs)} 个目录")
            return True
        except Exception as e:
            self._log('error', f"配置热加载启动失败: {e}")
            return False
    
    def stop(self):
        """停止配置监控"""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._log('info', "配置热加载已停止")
