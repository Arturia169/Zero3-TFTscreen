"""线程安全的数据存储中心"""
import threading
from typing import Dict, Any, Optional


class DataStore:
    """线程安全的数据存储"""
    
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {
            # 天气数据
            "temp": "--",
            "text": "...",
            "aqi": "0",
            "life": "",
            "feelsLike": "--",
            "humidity": "--",
            "windSpeed": "--",
            "windDir": "--",
            "today": {},
            "forecast": [],
            
            # 系统监控
            "cpu_t": 0,
            "cpu_u": 0.0,
            "ip": "Init...",
            "ram": 0,
            "disk": 0,
            "uptime": "",
            
            # 加密货币
            "crypto": [],
            "crypto_status": "Loading...",
            "crypto_klines": {},  # K线数据
            "crypto_history": {},  # 历史价格
            "bybit_asset": "Loading...",
            "bybit_asset_value": 0.0,
            "bybit_asset_history": [],
            
            # 网络和服务状态
            "network_status": "OK",
            "service_status": {},
            
            # Beszel 监控
            "beszel_clients": [],
            "beszel_status": "Loading...",
            "beszel_last_update": 0,
            
            # 物流追踪
            "tracking_packages": [],
            "tracking_status": "Loading...",
            "tracking_last_update": 0,
            "tracking_force_update": False,
            
            # B站监控
            "bilibili_streamers": [],
            "bilibili_status": "Loading...",
            "bilibili_last_update": 0,
            "bilibili_user": {},
            
            # Telegram 消息
            "telegram_messages": [],
            "telegram_status": "Loading...",
            "telegram_last_update": 0,
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取数据"""
        with self._lock:
            return self._data.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置数据"""
        with self._lock:
            self._data[key] = value
    
    def update(self, updates: Dict[str, Any]) -> None:
        """批量更新数据"""
        with self._lock:
            self._data.update(updates)
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        with self._lock:
            return self._data[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """支持字典式设置"""
        with self._lock:
            self._data[key] = value
