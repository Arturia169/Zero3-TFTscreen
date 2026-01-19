"""系统监控 Worker"""
import psutil
import socket
import os
from datetime import datetime
from .base import BaseWorker


class SystemWorker(BaseWorker):
    """系统监控线程"""
    
    def _get_local_ip(self) -> str:
        """获取本地IP地址"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(('8.8.8.8', 80))
                return s.getsockname()[0]
        except Exception as e:
            self._log('debug', f"获取IP失败: {e}")
            return "N/A"
    
    def _get_cpu_temperature(self) -> int:
        """获取CPU温度（摄氏度）"""
        try:
            temp_path = "/sys/class/thermal/thermal_zone0/temp"
            if os.path.exists(temp_path):
                with open(temp_path, "r") as f:
                    return int(float(f.read().strip()) / 1000)
        except Exception as e:
            self._log('debug', f"读取CPU温度失败: {e}")
        return 0
    
    def _format_uptime(self, boot_time: float) -> str:
        """格式化运行时间"""
        try:
            boot_dt = datetime.fromtimestamp(boot_time)
            delta = datetime.now() - boot_dt
            hours = delta.seconds // 3600
            return f"{delta.days}天{hours}时"
        except Exception:
            return "0天0时"
    
    def update(self) -> None:
        """更新系统监控数据"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            
            # IP地址
            ip = self._get_local_ip()
            
            # CPU温度
            cpu_temp = self._get_cpu_temperature()
            
            # 内存使用率
            mem_percent = psutil.virtual_memory().percent
            
            # 磁盘使用率
            disk_percent = psutil.disk_usage('/').percent
            
            # 运行时间
            uptime = self._format_uptime(psutil.boot_time())
            
            # 更新到数据存储
            self.data_store.update({
                "cpu_u": cpu_percent,
                "ip": ip,
                "cpu_t": cpu_temp,
                "ram": mem_percent,
                "disk": disk_percent,
                "uptime": uptime
            })
            
        except Exception as e:
            self._log('error', f"系统监控异常: {e}")
