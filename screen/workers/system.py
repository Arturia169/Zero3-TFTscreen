"""系统监控 Worker"""
import psutil
import socket
from datetime import datetime
from .base import BaseWorker


class SystemWorker(BaseWorker):
    """系统监控线程"""
    
    def update(self) -> None:
        """更新系统监控数据"""
        try:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=0.5)
            
            # CPU 温度
            cpu_temp = self._get_cpu_temperature()
            
            # 内存使用率
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            
            # 运行时间
            boot_time = psutil.boot_time()
            uptime = self._format_uptime(boot_time)
            
            # IP 地址
            ip = self._get_local_ip()
            
            # 更新到数据存储
            self.data_store.update({
                "cpu_u": cpu_percent,
                "cpu_t": cpu_temp,
                "ram": mem_percent,
                "disk": disk_percent,
                "uptime": uptime,
                "ip": ip
            })
            
        except Exception as e:
            self._log('error', f"Failed to update system data: {e}")
    
    def _get_cpu_temperature(self) -> float:
        """获取 CPU 温度"""
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp = float(f.read().strip()) / 1000.0
                return temp
        except:
            return 0.0
    
    def _format_uptime(self, boot_time: float) -> str:
        """格式化运行时间"""
        try:
            uptime_seconds = datetime.now().timestamp() - boot_time
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            return f"{days}天{hours}时"
        except:
            return "0天0时"
    
    def _get_local_ip(self) -> str:
        """获取本地 IP 地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "N/A"
