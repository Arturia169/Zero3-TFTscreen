#!/root/screen_test/bin/python
"""
智能屏幕显示系统
支持天气、GitHub监控、加密货币、日历等功能
"""
import time
import spidev
import os
import io
import threading
import requests
import psutil
import socket
import urllib3
import numpy as np
import calendar
import textwrap
import re
import hmac
import hashlib
import json
import logging
from typing import Dict, List, Tuple, Optional, Callable
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from zhdate import ZhDate
from datetime import datetime, timedelta

# 导入新的模块化 Worker
from screen.workers.system import SystemWorker

# 配置热加载
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object
    logger.warning("watchdog 库未安装，配置热加载不可用")

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
# 日志级别：DEBUG < INFO < WARNING < ERROR < CRITICAL
LOG_LEVEL = logging.INFO  # 改为INFO减少日志量
LOG_FILE = "/tmp/rili_screen.log"
LOG_MAX_SIZE = 5 * 1024 * 1024  # 5MB
LOG_BACKUP_COUNT = 2  # 保留2个备份

from logging.handlers import RotatingFileHandler

# 配置日志处理器
handlers = []
# 控制台输出
console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL)
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)
handlers.append(console_handler)

# 文件输出（带轮转）
if LOG_FILE:
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE, 
            maxBytes=LOG_MAX_SIZE,
            backupCount=LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setLevel(LOG_LEVEL)
        file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    except Exception as e:
        print(f"无法创建日志文件 {LOG_FILE}: {e}")

logging.basicConfig(
    level=LOG_LEVEL,
    handlers=handlers
)
logger = logging.getLogger(__name__)
logger.info(f"日志系统已初始化，级别: {logging.getLevelName(LOG_LEVEL)}, 最大: {LOG_MAX_SIZE//1024//1024}MB")

# ================= 1. 配置区域 =================
# 天气配置
QWEATHER_KEY = "04cdddbc959545bb89dd599ce28e0cb7"
CITY_ID = "101130601"
WEATHER_UPDATE_INTERVAL = 1800  # 30分钟

# 硬件配置
DC, RST, CS = "75", "79", "233" 
BUTTON_PIN = "70"  # PC6引脚
W, H = 320, 240
SPI_BUS = 1
SPI_DEVICE = 0
SPI_MAX_SPEED = 62500000  # 62.5MHz - ST7789最大支持速度

# 代理配置（支持环境变量）
PROXIES = {
    "http": os.environ.get("http_proxy", "http://192.168.5.100:7890"),
    "https": os.environ.get("https_proxy", "http://192.168.5.100:7890")
}

# Bybit配置
BYBIT_API_KEY = "onaDJGAOJfa8ZGjUeo"
BYBIT_SECRET = "NU0v7kpv1Wr2eZQFMeHfFtMhXgH2ScTnolZj"
BYBIT_FIXED_BALANCE = 0  # 不再使用固定余额
CRYPTO_UPDATE_INTERVAL = 15  # 15秒

# 倒数日配置
TARGET_DATE = datetime(2026, 2, 17)
TARGET_NAME = "CNY 2026"

# 加密货币配置
CRYPTO_SYMBOLS = ["BTCUSDT", "ETHUSDT", "DOGEUSDT"]

# 获取当前脚本所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Telegram配置
TELEGRAM_CONFIG_FILE = os.environ.get("TELEGRAM_CONFIG_PATH", os.path.join(BASE_DIR, "telegram_config.json"))  # Telegram配置文件
TELEGRAM_CHANNELS_FILE = os.environ.get("TELEGRAM_CHANNELS_PATH", os.path.join(BASE_DIR, "telegram_channels.json"))  # 频道列表文件
TELEGRAM_UPDATE_INTERVAL = 60  # 更新间隔（秒）

# 夜间模式配置 (01:30-08:00)
NIGHT_MODE_START_HOUR = 1
NIGHT_MODE_START_MINUTE = 30
NIGHT_MODE_END_HOUR = 8
NIGHT_MODE_END_MINUTE = 0
NIGHT_DARKNESS_FACTOR = 0.6

# ================= UI 绘图常量 =================
UI_PADDING = 4              # 通用内边距
UI_PADDING_SM = 2           # 小内边距
UI_LINE_HEIGHT = 12         # 行高
UI_HEADER_HEIGHT = 24       # 标题栏高度
UI_FOOTER_HEIGHT = 16       # 底部栏高度
UI_CARD_RADIUS = 6          # 卡片圆角
UI_CARD_GAP = 4             # 卡片间距
UI_CHAR_WIDTH_CN = 10       # 中文字符宽度
UI_CHAR_WIDTH_EN = 6        # 英文字符宽度

# 系统监控配置
SYSTEM_UPDATE_INTERVAL = 2  # 2秒

# 远程控制配置
CONTROL_UDP_PORT = 9998  # 用于远程控制的UDP端口

# 按键配置 - 全新优化的按钮系统
BUTTON_ENABLED = False  # 彻底禁用按钮 - GPIO有硬件问题
BUTTON_DEBOUNCE_TIME = 0.05  # 防抖时间（秒）
BUTTON_SAMPLE_INTERVAL = 0.005  # 采样间隔
BUTTON_MIN_PRESS_TIME = 0.1  # 最小有效按压时间
BUTTON_CHECK_INTERVAL = 0.02  # 主循环检查间隔

# 显示配置
DISPLAY_REFRESH_INTERVAL = 0.05  # 降低到50ms，提高响应速度
MAX_PAGES = 7  # 时钟、物流、B站、加密货币、日历、Beszel、Telegram
AUTO_PAGE_SWITCH_ENABLED = False  # 确保自动切换也被禁用
AUTO_PAGE_SWITCH_INTERVAL = 10  # 自动切换间隔（秒）

# 物流追踪配置
TRACKING_API_URL = "https://uapis.cn/api/v1/misc/tracking/query"
TRACKING_UPDATE_INTERVAL = 43200  # 12小时更新一次
TRACKING_DATA_FILE = "/tmp/tracking_packages.json"  # 包裹数据存储
TRACKING_WEB_PORT = 8080  # Web管理界面端口

# B站直播监控配置
BILIBILI_LIVE_API_URL = "https://uapis.cn/api/v1/social/bilibili/liveroom"
BILIBILI_UPDATE_INTERVAL = 3600  # 1小时更新一次
BILIBILI_DATA_FILE = os.environ.get("BILIBILI_DATA_PATH", "/tmp/bilibili_streamers.json")  # 主播数据存储
BILIBILI_SESSDATA = "f8f311b2%2C1782930150%2C5218a%2A11CjBHM5kN0mat4on-E4RobPSKdzVyfHkLA6wi5jqlO4ZmCBNfXK5wZTrzyh5VOwEzbXkSVkE3Y0V0SmpGcEVyNHIyak5wZ0hjYXpGd3lra2xvM1NjUHV5TW5XdUc5X05tT0hZVThZem9feFJJSTlqU3ROSXpjeUQ5c3VGanFWSUFRX1NfLTdfeEFRIIEC"

# Beszel服务器监控配置
BESZEL_API_URL = "http://192.168.5.100:8090"
BESZEL_API_BASE = f"{BESZEL_API_URL}/api"  # PocketBase API 基础路径
BESZEL_UPDATE_INTERVAL = 60  # 60秒更新一次，加快刷新速度
# Beszel身份验证信息
BESZEL_AUTH_EMAIL = "169hanser@gmail.com"
BESZEL_AUTH_PASSWORD = "ljl2001."

# ================= 2. 硬件驱动 =================
try:
    spi = spidev.SpiDev()
    spi.open(SPI_BUS, SPI_DEVICE)
    spi.max_speed_hz = SPI_MAX_SPEED
    spi.mode = 0
    logger.info("SPI初始化成功")
except Exception as e:
    logger.error(f"SPI初始化失败: {e}")
    spi = None


def gpio_set(pin: str, value: int) -> None:
    """设置GPIO引脚值"""
    try:
        os.system(f"echo {value} > /sys/class/gpio/gpio{pin}/value 2>/dev/null")
    except Exception as e:
        logger.warning(f"GPIO设置失败 pin={pin}, value={value}: {e}")


def init_gpio(pin: str, direction: str = "out") -> bool:
    """初始化GPIO引脚"""
    try:
        gpio_path = f"/sys/class/gpio/gpio{pin}"
        if not os.path.exists(gpio_path):
            os.system(f"echo {pin} > /sys/class/gpio/export 2>/dev/null")
        time.sleep(0.1)
        os.system(f"echo {direction} > {gpio_path}/direction 2>/dev/null")
        return True
    except Exception as e:
        logger.error(f"GPIO初始化失败 pin={pin}: {e}")
        return False


def init_button_gpio() -> bool:
    """初始化按键GPIO"""
    return init_gpio(BUTTON_PIN, "in")


def read_button_raw() -> bool:
    """读取按键原始状态"""
    try:
        with open(f"/sys/class/gpio/gpio{BUTTON_PIN}/value", "r") as f:
            return f.read().strip() == "0"
    except Exception as e:
        logger.debug(f"读取按键失败: {e}")
        return False


def write_cmd(cmd: int) -> None:
    """写入命令到显示器"""
    if spi is None:
        return
    try:
        gpio_set(CS, 0)
        gpio_set(DC, 0)
        spi.writebytes([cmd])
        gpio_set(CS, 1)
    except Exception as e:
        logger.error(f"写入命令失败 cmd=0x{cmd:02X}: {e}")


def write_data(data) -> None:
    """写入数据到显示器"""
    if spi is None:
        return
    try:
        gpio_set(CS, 0)
        gpio_set(DC, 1)
        if isinstance(data, int):
            spi.writebytes([data])
        else:
            spi.writebytes(list(data))
        gpio_set(CS, 1)
    except Exception as e:
        logger.error(f"写入数据失败: {e}")

def init_display() -> bool:
    """初始化显示器"""
    try:
        # 初始化按键GPIO
        init_button_gpio()
        
        # 初始化显示器控制GPIO
        for pin in [DC, RST, CS]:
            if not init_gpio(pin, "out"):
                logger.error(f"显示器GPIO初始化失败: {pin}")
                return False
        
        # 硬件复位
        gpio_set(RST, 0)
        time.sleep(0.1)
        gpio_set(RST, 1)
        time.sleep(0.1)
        
        # 初始化序列
        write_cmd(0x01)  # Software reset
        time.sleep(0.1)
        write_cmd(0x11)  # Sleep out
        time.sleep(0.1)
        write_cmd(0x36)  # Memory access control
        write_data(0x28)
        write_cmd(0x3A)  # Pixel format
        write_data(0x55)  # 16-bit RGB565
        write_cmd(0x29)  # Display on
        
        logger.info("显示器初始化成功")
        import sys
        sys.stdout.flush()
        sys.stderr.flush()
        return True
    except Exception as e:
        logger.error(f"显示器初始化失败: {e}")
        return False

def rgb_to_rgb565(r: int, g: int, b: int) -> int:
    """将RGB888转换为RGB565格式"""
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def image_to_rgb565_bytes(image: Image.Image) -> bytes:
    """使用 NumPy 向量化操作将 PIL 图像转换为 RGB565 字节数组 (性能提升约 50-100 倍)"""
    # 确保图像为 RGB 模式并转换为 numpy 数组
    img_array = np.array(image.convert("RGB"), dtype=np.uint16)
    
    # 提取 R, G, B 通道
    r = img_array[:, :, 0]
    g = img_array[:, :, 1]
    b = img_array[:, :, 2]
    
    # 转换为 RGB565: (R & 0xF8) << 8 | (G & 0xFC) << 3 | (B >> 3)
    # NumPy 会并行处理所有像素
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    
    # 将 16 位整数数组转换为大端序字节
    return rgb565.byteswap().tobytes()


def display_image(image: Image.Image) -> None:
    """在显示器上显示图像 - 优化版"""
    if spi is None:
        return
    
    try:
        # 设置显示窗口 (320x240)
        write_cmd(0x2A)  # Column address set
        write_data([0x00, 0x00, 0x01, 0x3F])
        write_cmd(0x2B)  # Row address set
        write_data([0x00, 0x00, 0x00, 0xEF])
        write_cmd(0x2C)  # Memory write
        
        gpio_set(CS, 0)
        gpio_set(DC, 1)
        
        # 转换并发送像素数据
        pixels = image_to_rgb565_bytes(image)
        spi.writebytes2(pixels)
        
        gpio_set(CS, 1)
    except Exception as e:
        logger.error(f"显示图像失败: {e}")
        # 尝试重新初始化SPI
        try:
            if spi:
                spi.close()
            time.sleep(0.1)
            init_display()
        except:
            pass


def clear_display() -> None:
    """清空显示器"""
    if spi is None:
        return
    try:
        write_cmd(0x2C)  # Memory write
        gpio_set(CS, 0)
        gpio_set(DC, 1)
        # 发送全黑数据
        spi.writebytes2(bytearray(W * H * 2))
        gpio_set(CS, 1)
    except Exception as e:
        logger.error(f"清空显示器失败: {e}")

# ================= 3. 数据中心 =================
class DataStore:
    """线程安全的数据存储"""
    def __init__(self):
        self._lock = threading.Lock()
        self._data = {
            "temp": "--",
            "text": "...",
            "aqi": "0",
            "life": "",
            "feelsLike": "--",
            "humidity": "--",
            "windSpeed": "--",
            "windDir": "--",
            "today": {},
            "cpu_t": 0,
            "cpu_u": 0.0,
            "ip": "Init...",
            "forecast": [],
            "ram": 0,
            "disk": 0,
            "uptime": "",
            "crypto": [],
            "crypto_status": "Loading...",
            "bybit_asset": "Loading...",
            "bybit_asset_value": 0.0,  # 数值形式的资产
            "bybit_asset_history": [],  # 资产历史记录 [(timestamp, value), ...]
            "crypto_history": {},  # 币种历史价格 {"BTC": [(timestamp, price), ...], ...}
            "network_status": "OK",
            "service_status": {},
            "beszel_clients": [],
            "beszel_status": "Loading...",
            "beszel_last_update": 0,
            "tracking_packages": [],
            "tracking_status": "Loading...",
            "tracking_last_update": 0,
            "tracking_force_update": False,  # 强制立即更新标志
            "bilibili_streamers": [],
            "bilibili_status": "Loading...",
            "bilibili_last_update": 0,
            "bilibili_user": {}
        }
    
    def get(self, key: str, default=None):
        """获取数据"""
        with self._lock:
            return self._data.get(key, default)
    
    def set(self, key: str, value) -> None:
        """设置数据"""
        with self._lock:
            self._data[key] = value
    
    def update(self, updates: Dict) -> None:
        """批量更新数据"""
        with self._lock:
            self._data.update(updates)
    
    def __getitem__(self, key: str):
        """支持字典式访问"""
        with self._lock:
            return self._data[key]
    
    def __setitem__(self, key: str, value) -> None:
        """支持字典式设置"""
        with self._lock:
            self._data[key] = value


info = DataStore()


# ================= 配置热加载 =================
class ConfigReloader(FileSystemEventHandler):
    """配置文件热加载器"""
    
    def __init__(self):
        self._callbacks: Dict[str, List[Callable]] = {}  # 文件路径 -> 回调函数列表
        self._last_modified: Dict[str, float] = {}  # 防抖：记录最后修改时间
        self._debounce_seconds = 1.0  # 防抖时间
        self._observer = None
        self._watched_dirs = set()
    
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
        
        logger.info(f"注册配置热加载: {file_path}")
    
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
            logger.info(f"检测到配置变更: {file_path}")
            for callback in self._callbacks.get(file_path, []):
                try:
                    callback()
                    logger.info(f"配置重载成功: {file_path}")
                except Exception as e:
                    logger.error(f"配置重载失败 {file_path}: {e}")
        
        threading.Thread(target=delayed_reload, daemon=True).start()
    
    def start(self) -> bool:
        """启动配置监控"""
        if not WATCHDOG_AVAILABLE:
            logger.warning("watchdog 库未安装，配置热加载不可用。安装: pip install watchdog")
            return False
        
        try:
            self._observer = Observer()
            
            # 监控所有已注册的目录
            for dir_path in self._watched_dirs:
                if os.path.exists(dir_path):
                    self._observer.schedule(self, dir_path, recursive=False)
            
            self._observer.start()
            logger.info(f"配置热加载已启动，监控 {len(self._watched_dirs)} 个目录")
            return True
        except Exception as e:
            logger.error(f"配置热加载启动失败: {e}")
            return False
    
    def stop(self):
        """停止配置监控"""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            logger.info("配置热加载已停止")


# 全局配置重载器
config_reloader = ConfigReloader()


# 配置重载回调函数
def reload_tracking_config():
    """重载物流追踪配置"""
    info["tracking_force_update"] = True
    logger.info("物流配置已重载，将立即更新")


def reload_bilibili_config():
    """重载B站主播配置"""
    # 触发下次循环重新加载
    info["bilibili_last_update"] = 0
    logger.info("B站配置已重载")


def reload_telegram_config():
    """重载Telegram配置"""
    info["telegram_status"] = "Reloading..."
    logger.info("Telegram配置已重载")


# 注册配置文件监控
config_reloader.register(TRACKING_DATA_FILE, reload_tracking_config)
config_reloader.register(BILIBILI_DATA_FILE, reload_bilibili_config)
config_reloader.register(TELEGRAM_CONFIG_FILE, reload_telegram_config)
config_reloader.register(TELEGRAM_CHANNELS_FILE, reload_telegram_config)


def weather_worker() -> None:
    """天气数据更新工作线程"""
    while True:
        try:
            base_url = "https://devapi.qweather.com/v7"
            urls = {
                "now": f"{base_url}/weather/now?location={CITY_ID}&key={QWEATHER_KEY}",
                "forecast": f"{base_url}/weather/3d?location={CITY_ID}&key={QWEATHER_KEY}",
                "air": f"{base_url}/air/now?location={CITY_ID}&key={QWEATHER_KEY}",
                "life": f"{base_url}/indices/1d?type=3&location={CITY_ID}&key={QWEATHER_KEY}"
            }
            
            responses = {}
            for key, url in urls.items():
                try:
                    resp = requests.get(url, timeout=10)
                    resp.raise_for_status()
                    responses[key] = resp.json()
                except requests.RequestException as e:
                    logger.warning(f"天气API请求失败 {key}: {e}")
                    responses[key] = {}
            
            # 更新当前天气
            if responses.get("now", {}).get("code") == "200":
                now_data = responses["now"]["now"]
                info.update({
                    "temp": now_data.get("temp", "--"),
                    "text": now_data.get("text", "..."),
                    "feelsLike": now_data.get("feelsLike", "--"),
                    "humidity": now_data.get("humidity", "--"),
                    "windSpeed": now_data.get("windSpeed", "--"),
                    "windDir": now_data.get("windDir", "--")
                })
            
            # 更新预报
            if responses.get("forecast", {}).get("code") == "200":
                forecast_data = responses["forecast"].get("daily", [])
                info["forecast"] = forecast_data
                # 保存今天的预报数据
                if forecast_data:
                    info["today"] = forecast_data[0]
            
            # 更新空气质量
            if responses.get("air", {}).get("code") == "200":
                info["aqi"] = responses["air"]["now"].get("aqi", "0")
            
            # 更新生活指数
            if responses.get("life", {}).get("code") == "200":
                life_data = responses["life"].get("daily", [])
                if life_data:
                    info["life"] = life_data[0].get("category", "")
            
            logger.debug("天气数据更新成功")
            time.sleep(WEATHER_UPDATE_INTERVAL)
            
        except Exception as e:
            logger.error(f"天气更新线程异常: {e}")
            time.sleep(10)

def get_local_ip() -> str:
    """获取本地IP地址"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            return s.getsockname()[0]
    except Exception as e:
        logger.debug(f"获取IP失败: {e}")
        return "N/A"


def get_cpu_temperature() -> int:
    """获取CPU温度（摄氏度）"""
    try:
        temp_path = "/sys/class/thermal/thermal_zone0/temp"
        if os.path.exists(temp_path):
            with open(temp_path, "r") as f:
                return int(float(f.read().strip()) / 1000)
    except Exception as e:
        logger.debug(f"读取CPU温度失败: {e}")
    return 0


def format_uptime(boot_time: float) -> str:
    """格式化运行时间"""
    try:
        boot_dt = datetime.fromtimestamp(boot_time)
        delta = datetime.now() - boot_dt
        hours = delta.seconds // 3600
        return f"{delta.days}天{hours}时"
    except Exception:
        return "0天0时"


def system_worker() -> None:
    """系统监控工作线程"""
    while True:
        try:
            # CPU使用率
            info["cpu_u"] = psutil.cpu_percent(interval=None)
            
            # IP地址
            info["ip"] = get_local_ip()
            
            # CPU温度
            info["cpu_t"] = get_cpu_temperature()
            
            # 内存使用率
            info["ram"] = psutil.virtual_memory().percent
            
            # 磁盘使用率
            info["disk"] = psutil.disk_usage('/').percent
            
            # 运行时间
            info["uptime"] = format_uptime(psutil.boot_time())
            
        except Exception as e:
            logger.error(f"系统监控异常: {e}")
        
        time.sleep(SYSTEM_UPDATE_INTERVAL)


def get_bybit_signature(api_key: str, secret: str, params: Dict) -> Tuple[str, str, str, str]:
    """生成Bybit API签名"""
    timestamp = str(int(time.time() * 1000))
    recv_window = "5000"
    param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    sign_str = timestamp + api_key + recv_window + param_str
    signature = hmac.new(
        secret.encode("utf-8"),
        sign_str.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return timestamp, recv_window, signature, param_str

def format_crypto_price(price: float) -> str:
    """格式化加密货币价格显示"""
    if price < 1:
        return f"{price:.4f}"
    elif price < 10:
        return f"{price:.3f}"
    else:
        return f"{price:.2f}"


def get_binance_prices() -> List[Dict]:
    """获取Binance价格数据"""
    crypto_data = []
    for symbol in CRYPTO_SYMBOLS:
        try:
            url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
            res = requests.get(url, proxies=PROXIES, timeout=10, verify=False)
            res.raise_for_status()
            data = res.json()
            
            price = float(data['lastPrice'])
            crypto_data.append({
                "name": symbol.replace("USDT", ""),
                "price": format_crypto_price(price),
                "change": float(data['priceChangePercent'])
            })
        except Exception as e:
            logger.warning(f"获取币安价格失败 {symbol}: {e}")
    
    return crypto_data


def get_bybit_kline(symbol: str, interval: str = "15", limit: int = 20) -> List[Dict]:
    """
    获取Bybit K线数据
    symbol: 交易对，如 BTCUSDT
    interval: K线周期，1/3/5/15/30/60/120/240/360/720/D/W/M
    limit: 获取数量，最大200
    返回: [{open, high, low, close, volume, timestamp}, ...]
    """
    try:
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            "category": "spot",
            "symbol": symbol,
            "interval": interval,
            "limit": limit
        }
        
        res = requests.get(url, params=params, proxies=PROXIES, timeout=10, verify=False)
        res.raise_for_status()
        data = res.json()
        
        if data.get("retCode") == 0:
            klines = []
            # Bybit返回格式: [timestamp, open, high, low, close, volume, turnover]
            # 按时间倒序返回，需要反转
            raw_list = data.get("result", {}).get("list", [])
            for item in reversed(raw_list):
                klines.append({
                    "timestamp": int(item[0]),
                    "open": float(item[1]),
                    "high": float(item[2]),
                    "low": float(item[3]),
                    "close": float(item[4]),
                    "volume": float(item[5])
                })
            return klines
        else:
            logger.warning(f"Bybit K线API错误: {data.get('retMsg')}")
            return []
    except Exception as e:
        logger.error(f"获取Bybit K线失败 {symbol}: {e}")
        return []


def get_bybit_balance() -> float:
    """获取Bybit账户余额"""
    total_val = 0.0
    
    endpoints = {
        "UNIFIED": "https://api.bybit.com/v5/account/wallet-balance",
        "FUND": "https://api.bybit.com/v5/asset/transfer/query-account-coins-balance"
    }
    
    for acc_type, endpoint in endpoints.items():
        try:
            params = {"accountType": acc_type}
            ts, win, sign, query = get_bybit_signature(BYBIT_API_KEY, BYBIT_SECRET, params)
            headers = {
                "X-BAPI-API-KEY": BYBIT_API_KEY,
                "X-BAPI-SIGN": sign,
                "X-BAPI-TIMESTAMP": ts,
                "X-BAPI-RECV-WINDOW": win
            }
            
            res = requests.get(
                f"{endpoint}?{query}",
                headers=headers,
                proxies=PROXIES,
                timeout=10,
                verify=False
            )
            res.raise_for_status()
            data = res.json()
            
            if data.get("retCode") == 0:
                if acc_type == "UNIFIED":
                    balance_list = data.get("result", {}).get("list", [])
                    if balance_list:
                        total_val += float(balance_list[0].get("totalEquity", 0))
                else:
                    balance_list = data.get("result", {}).get("balance", [])
                    for b in balance_list:
                        total_val += float(b.get("walletBalance", 0))
            else:
                logger.warning(f"Bybit API返回错误 {acc_type}: {data.get('retMsg')}")
                
        except Exception as e:
            logger.error(f"获取Bybit余额失败 {acc_type}: {e}")
    
    return total_val + BYBIT_FIXED_BALANCE


def crypto_worker() -> None:
    """加密货币监控工作线程"""
    
    while True:
        try:
            # 获取币安价格（用于显示当前价格和涨跌幅）
            crypto_data = get_binance_prices()
            if crypto_data:
                info["crypto"] = crypto_data
                info["crypto_status"] = "Updated"
            else:
                info["crypto_status"] = "Market Err"
            
            # 获取Bybit真实K线数据
            kline_data = {}
            for symbol in CRYPTO_SYMBOLS:
                coin_name = symbol.replace("USDT", "")
                klines = get_bybit_kline(symbol, interval="15", limit=20)
                if klines:
                    kline_data[coin_name] = klines
                    logger.debug(f"获取 {coin_name} K线数据: {len(klines)} 条")
            
            if kline_data:
                info["crypto_klines"] = kline_data
                logger.info(f"K线数据更新完成: {list(kline_data.keys())}")
            
        except Exception as e:
            logger.error(f"加密货币更新异常: {e}")
            info["crypto_status"] = "Market Err"

        # 获取Bybit余额
        if BYBIT_API_KEY == "你的API_KEY" or not BYBIT_API_KEY:
            info["bybit_asset"] = "Set API Key!"
        else:
            try:
                total_val = get_bybit_balance()
                info["bybit_asset"] = f"${total_val:,.2f}"
                info["bybit_asset_value"] = total_val
                
                # 记录资产历史
                current_time = time.time()
                asset_history = info.get("bybit_asset_history", [])
                asset_history.append((current_time, total_val))
                
                # 只保留最近的数据点
                if len(asset_history) > 20:
                    asset_history = asset_history[-20:]
                
                info["bybit_asset_history"] = asset_history
            except Exception as e:
                logger.error(f"Bybit余额更新失败: {e}")
                info["bybit_asset"] = "Sync Err"
        
        time.sleep(CRYPTO_UPDATE_INTERVAL)


def beszel_worker() -> None:
    """Beszel服务器监控工作线程 - 使用PocketBase API"""
    auth_token = None
    # 存储上一次的网络数据，用于计算速度（差值）
    prev_network_data = {}  # {system_name: {"bb": value, "u": value, "time": timestamp}}
    
    while True:
        try:
            # 如果需要身份验证，先尝试登录
            # 根据 https://github.com/gethomepage/homepage/discussions/5125
            # Beszel需要使用superuser账户进行API认证，端点应为 _superusers/auth-with-password
            if BESZEL_AUTH_EMAIL and BESZEL_AUTH_PASSWORD and not auth_token:
                try:
                    # 使用superuser认证端点
                    auth_url = f"{BESZEL_API_BASE}/collections/_superusers/auth-with-password"
                    auth_data = {
                        "identity": BESZEL_AUTH_EMAIL,
                        "password": BESZEL_AUTH_PASSWORD
                    }
                    auth_resp = requests.post(
                        auth_url,
                        json=auth_data,
                        timeout=10,
                        verify=False,
                        proxies=PROXIES if PROXIES else None
                    )
                    if auth_resp.status_code == 200:
                        auth_result = auth_resp.json()
                        auth_token = auth_result.get("token")
                        if auth_token:
                            logger.info("Beszel身份验证成功（superuser）")
                        else:
                            logger.warning("Beszel身份验证响应中未找到token")
                            auth_token = auth_resp.headers.get("Authorization", "").replace("Bearer ", "")
                    else:
                        error_text = auth_resp.text[:300] if auth_resp.text else "无错误详情"
                        logger.error(f"Beszel身份验证失败，状态码: {auth_resp.status_code}, 响应: {error_text}")
                        logger.warning("请确保使用的是PocketBase的superuser账户（可在 <beszel-url>/_/#/login 登录）")
                except Exception as e:
                    logger.error(f"Beszel身份验证异常: {e}")
                    auth_token = None
            
            # 使用PocketBase API格式获取systems集合
            # API格式: /api/collections/{collection}/records
            systems_url = f"{BESZEL_API_BASE}/collections/systems/records"
            
            # 准备请求参数
            # 根据错误信息，systems集合中没有"latest"关系字段
            # 直接查询systems集合，监控数据可能直接存储在记录字段中
            params = {
                "page": 1,
                "perPage": 10,
                "sort": "-created"  # 按创建时间降序
            }
            
            clients_data = []
            
            headers = {
                'User-Agent': 'OrangePi-Monitor/1.0',
                'Content-Type': 'application/json'
            }
            
            # 如果已认证，添加token
            if auth_token:
                headers['Authorization'] = f'Bearer {auth_token}'
            
            # 发送请求（不使用expand，避免关系字段错误）
            try:
                resp = requests.get(
                    systems_url,
                    params=params,
                    headers=headers,
                    timeout=15,
                    verify=False,
                    proxies=PROXIES if PROXIES else None
                )
                
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        # PocketBase返回格式：{"page": 1, "perPage": 20, "totalItems": X, "items": [...]}
                        if isinstance(data, dict):
                            if "items" in data:
                                clients_data = data["items"]
                            elif "data" in data:
                                clients_data = data["data"] if isinstance(data["data"], list) else [data["data"]]
                            else:
                                # 可能是单个记录对象
                                clients_data = [data]
                        elif isinstance(data, list):
                            clients_data = data
                        else:
                            clients_data = []
                        
                        if clients_data:
                            logger.info(f"Beszel API返回 {len(clients_data)} 条记录")
                            # 调试：输出第一条记录的结构（完整结构用于调试）
                            sample_data = json.dumps(clients_data[0], ensure_ascii=False, indent=2)
                            logger.info(f"Beszel第一条记录结构: {sample_data[:1500]}")
                    except ValueError as e:
                        logger.error(f"Beszel API响应JSON解析失败: {e}, 响应内容: {resp.text[:300]}")
                        info["beszel_status"] = "Parse Error"
                elif resp.status_code == 401:
                    logger.warning("Beszel API需要身份验证")
                    auth_token = None
                    info["beszel_status"] = "Auth Required"
                elif resp.status_code == 403:
                    logger.warning("Beszel API访问被拒绝")
                    auth_token = None
                    info["beszel_status"] = "Forbidden"
                elif resp.status_code == 404:
                    logger.warning("Beszel API端点不存在，可能需要检查集合名称")
                    info["beszel_status"] = "Not Found"
                else:
                    error_msg = resp.text[:200] if resp.text else "No error message"
                    logger.error(f"Beszel API返回状态码: {resp.status_code}, 错误: {error_msg}")
                    info["beszel_status"] = f"API Err {resp.status_code}"
                    
            except requests.Timeout:
                logger.error("Beszel API请求超时")
                info["beszel_status"] = "Timeout"
            except requests.RequestException as e:
                logger.error(f"Beszel API请求异常: {e}")
                info["beszel_status"] = "Network Err"
            
            if clients_data:
                # 处理客户端数据，提取关键信息
                processed_clients = []
                for client in clients_data[:5]:  # 最多显示5个客户端
                    try:
                        # 灵活提取数据，支持多种格式
                        def safe_get(data, *keys, default=0):
                            """安全获取嵌套数据"""
                            for key in keys:
                                if isinstance(data, dict):
                                    data = data.get(key)
                                elif isinstance(data, (list, tuple)) and isinstance(key, int):
                                    if 0 <= key < len(data):
                                        data = data[key]
                                    else:
                                        return default
                                else:
                                    return default
                                if data is None:
                                    return default
                            return data if data is not None else default
                        
                        # 根据实际数据结构，Beszel的监控数据存储在 info 字段中
                        # info 字段使用缩写：
                        # - cpu: CPU使用率 (%)
                        # - mp: 内存使用率 Memory Percent (%)
                        # - dp: 磁盘使用率 Disk Percent (%)
                        # - dt: 温度 Temperature (可能是磁盘温度或CPU温度)
                        # - la: 负载数组 Load Average [1分钟, 5分钟, 15分钟]
                        # - l1: 1分钟负载
                        # - bb: 可能是网络带宽或字节数
                        # - ns/nr: 网络速度（如果存在）
                        # - netSent/netRecv: 网络发送/接收（如果存在）
                        info_data = client.get("info", {})
                        if not isinstance(info_data, dict):
                            info_data = {}
                        
                        # 从 info 字段提取数据（优先）
                        cpu_val = info_data.get("cpu") or 0
                        mem_val = info_data.get("mp") or 0  # mp = Memory Percent
                        disk_val = info_data.get("dp") or 0  # dp = Disk Percent
                        temp_val = info_data.get("dt") or 0  # dt = 可能是温度
                        load_val = info_data.get("la") or info_data.get("l1") or [0, 0, 0]  # la = Load Average
                        
                        # 尝试多种方式提取网速数据
                        # Beszel可能使用不同的字段名，需要全面搜索
                        net_sent = (
                            info_data.get("ns") or
                            info_data.get("netSent") or
                            info_data.get("networkSent") or
                            info_data.get("tx") or
                            info_data.get("upload") or
                            0
                        )
                        net_recv = (
                            info_data.get("nr") or
                            info_data.get("netRecv") or
                            info_data.get("networkRecv") or
                            info_data.get("rx") or
                            info_data.get("download") or
                            0
                        )
                        
                        # 如果还是0，尝试从顶层字段获取
                        if not net_sent or net_sent == 0:
                            net_sent = (
                                client.get("netSent") or
                                client.get("networkSent") or
                                client.get("tx") or
                                safe_get(client, "network", "sent") or
                                safe_get(client, "network", "tx") or
                                0
                            )
                        
                        if not net_recv or net_recv == 0:
                            net_recv = (
                                client.get("netRecv") or
                                client.get("networkRecv") or
                                client.get("rx") or
                                safe_get(client, "network", "recv") or
                                safe_get(client, "network", "rx") or
                                0
                            )
                        
                        # 如果 info 中没有数据，尝试从顶层字段获取（向后兼容）
                        if not cpu_val or cpu_val == 0:
                            cpu_val = (
                                client.get("cpu") or
                                client.get("cpuUsage") or
                                safe_get(client, "metrics", "cpu") or
                                0
                            )
                        
                        if not mem_val or mem_val == 0:
                            mem_val = (
                                client.get("memory") or
                                client.get("memoryUsage") or
                                client.get("ram") or
                                safe_get(client, "metrics", "memory") or
                                0
                            )
                        
                        if not disk_val or disk_val == 0:
                            disk_val = (
                                client.get("disk") or
                                client.get("diskUsage") or
                                safe_get(client, "metrics", "disk") or
                                0
                            )
                        
                        if not temp_val or temp_val == 0:
                            temp_val = (
                                client.get("temperature") or
                                client.get("temp") or
                                safe_get(client, "metrics", "temperature") or
                                0
                            )
                        
                        # 处理负载数据
                        if isinstance(load_val, str):
                            try:
                                load_val = [float(x) for x in load_val.split()[:3]]
                            except:
                                load_val = [0, 0, 0]
                        elif isinstance(load_val, (int, float)):
                            # 如果只有一个数值，假设是1分钟负载
                            load_val = [float(load_val), 0, 0]
                        elif not isinstance(load_val, (list, tuple)) or len(load_val) < 3:
                            load_val = [0, 0, 0]
                        
                        # 提取服务信息（如果存在）
                        # 从数据结构看，服务信息可能不在当前返回的字段中
                        services_data = client.get("services") or client.get("serviceCount") or {}
                        if isinstance(services_data, dict):
                            services_total = services_data.get("total") or services_data.get("count") or 0
                            services_failed = services_data.get("failed") or services_data.get("failedCount") or 0
                        elif isinstance(services_data, (int, float)):
                            services_total = int(services_data)
                            services_failed = client.get("servicesFailed") or client.get("failedServices") or 0
                        else:
                            services_total = 0
                            services_failed = 0
                        
                        # 系统名称和状态
                        system_name = client.get("name") or client.get("hostname") or "Unknown"
                        status_val = client.get("status")  # status字段直接包含 "up" 或 "down"
                        if isinstance(status_val, dict):
                            status_val = status_val.get("status") or status_val.get("state")
                        
                        
                        # 从 'bb' 字段获取网络带宽数据（累计字节数，需要差值计算）
                        # 注意：'u' 字段是 uptime（运行秒数），不是网络上传
                        bb_val = info_data.get("bb") or 0
                        
                        # 如果还没有找到网速数据，从 'bb' 计算（差值法）
                        if net_sent == 0 and net_recv == 0 and bb_val > 0:
                            prev_data = prev_network_data.get(system_name)
                            current_time = time.time()
                            
                            if prev_data and prev_data.get("time"):
                                time_diff = current_time - prev_data["time"]
                                
                                if time_diff > 0 and prev_data.get("bb", 0) > 0:
                                    bb_diff = float(bb_val) - float(prev_data["bb"])
                                    # bb 可能是总带宽（上行+下行），分配为下行速度
                                    if bb_diff > 0:
                                        net_recv = bb_diff / time_diff
                                        # 估算上行速度（假设为下行的 10%）
                                        net_sent = net_recv * 0.1
                                    logger.debug(f"系统 {system_name} 网络: bb当前={bb_val}, bb上次={prev_data.get('bb')}, 差值={bb_diff}, 时间差={time_diff:.1f}s, 速度={net_recv:.2f}B/s")
                            
                            # 保存当前数据用于下次计算
                            prev_network_data[system_name] = {
                                "bb": bb_val,
                                "time": current_time
                            }
                        
                        # 确保数值类型正确
                        try:
                            cpu_val = float(cpu_val) if cpu_val else 0.0
                            mem_val = float(mem_val) if mem_val else 0.0
                            disk_val = float(disk_val) if disk_val else 0.0
                            temp_val = float(temp_val) if temp_val else 0.0
                            net_sent = float(net_sent) if net_sent else 0.0
                            net_recv = float(net_recv) if net_recv else 0.0
                        except (ValueError, TypeError):
                            cpu_val = mem_val = disk_val = temp_val = net_sent = net_recv = 0.0
                        
                        # 调试日志：输出提取的数据
                        logger.debug(f"系统 {system_name}: CPU={cpu_val}%, RAM={mem_val}%, DSK={disk_val}%, TEMP={temp_val}°, LOAD={load_val}, UP={net_sent:.1f}, DOWN={net_recv:.1f}")
                        
                        client_info = {
                            "name": str(system_name)[:15],
                            "status": str(status_val) if status_val else "unknown",
                            "cpu": cpu_val,
                            "memory": mem_val,
                            "disk": disk_val,
                            "temperature": temp_val,
                            "load": load_val[:3] if isinstance(load_val, (list, tuple)) else [0, 0, 0],
                            "network_up": net_sent,
                            "network_down": net_recv,
                            "services": int(services_total) if services_total else 0,
                            "services_failed": int(services_failed) if services_failed else 0
                        }
                        
                        processed_clients.append(client_info)
                    except Exception as e:
                        logger.debug(f"处理客户端数据失败: {e}")
                        continue
                
                if processed_clients:
                    info["beszel_clients"] = processed_clients
                    info["beszel_status"] = "Updated"
                    info["beszel_last_update"] = time.time()
                    logger.info(f"Beszel数据更新成功，获取到{len(processed_clients)}个客户端")
                else:
                    info["beszel_status"] = "No Data"
                    logger.warning("Beszel API返回数据但无法解析")
            else:
                info["beszel_status"] = "API Error"
                logger.warning("Beszel API无响应")
                
        except Exception as e:
            logger.error(f"Beszel更新线程异常: {e}")
            info["beszel_status"] = "Connection Err"
        
        time.sleep(BESZEL_UPDATE_INTERVAL)


def load_telegram_channels() -> List[str]:
    """加载Telegram频道列表"""
    try:
        if os.path.exists(TELEGRAM_CHANNELS_FILE):
            with open(TELEGRAM_CHANNELS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("channels", ["Seele_WW_Leak"])
    except Exception as e:
        logger.error(f"加载Telegram频道列表失败: {e}")
    return ["Seele_WW_Leak"]  # 默认频道


def save_telegram_channels(channels: List[str]) -> None:
    """保存Telegram频道列表"""
    try:
        with open(TELEGRAM_CHANNELS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"channels": channels}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存Telegram频道列表失败: {e}")


def load_telegram_config() -> Dict:
    """加载Telegram API配置"""
    try:
        if os.path.exists(TELEGRAM_CONFIG_FILE):
            with open(TELEGRAM_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"加载Telegram配置失败: {e}")
    return {"api_id": 0, "api_hash": ""}


def save_telegram_config(api_id: int, api_hash: str) -> None:
    """保存Telegram API配置"""
    try:
        with open(TELEGRAM_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({"api_id": api_id, "api_hash": api_hash}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存Telegram配置失败: {e}")


def telegram_worker() -> None:
    """Telegram频道消息监控工作线程"""
    import asyncio
    
    # 加载配置
    tg_config = load_telegram_config()
    api_id = tg_config.get("api_id", 0)
    api_hash = tg_config.get("api_hash", "")
    
    # 检查配置
    if not api_id or not api_hash:
        logger.warning("Telegram API未配置，跳过")
        info["telegram_status"] = "Not Configured"
        return
    
    try:
        from telethon import TelegramClient
        from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, DocumentAttributeVideo
        import socks
    except ImportError as e:
        logger.error(f"依赖未安装: {e}，请运行: pip install telethon pysocks")
        info["telegram_status"] = "Deps Missing"
        return
    
    async def fetch_messages():
        """异步获取频道消息"""
        session_path = os.path.join(os.path.dirname(__file__), 'telegram_session')
        
        # 配置代理
        proxy = None
        if PROXIES and PROXIES.get("http"):
            proxy_url = PROXIES.get("http", "")
            if proxy_url:
                try:
                    proxy_addr = proxy_url.replace("http://", "").replace("https://", "")
                    host, port = proxy_addr.split(":")
                    proxy = (socks.HTTP, host, int(port))
                    logger.info(f"Telegram使用代理: {host}:{port}")
                except Exception as e:
                    logger.error(f"解析代理地址失败: {e}")
        
        client = TelegramClient(session_path, api_id, api_hash, proxy=proxy)
        
        try:
            await client.start()
            logger.info("Telegram客户端已连接")
            
            while True:
                try:
                    # 加载频道列表
                    channels = load_telegram_channels()
                    if not channels:
                        channels = ["Seele_WW_Leak"]
                    
                    # 获取所有频道的消息
                    all_channel_data = []
                    telegram_thumbs = {}
                    
                    for channel_username in channels:
                        try:
                            # 获取频道实体
                            channel = await client.get_entity(channel_username)
                            channel_title = getattr(channel, 'title', channel_username)
                            
                            # 获取最新1条消息
                            messages = await client.get_messages(channel, limit=1)
                            
                            channel_data = {
                                "username": channel_username,
                                "title": channel_title,
                                "messages": []
                            }
                            
                            for msg in messages:
                                if msg is None:
                                    continue
                                
                                msg_data = {
                                    "id": msg.id,
                                    "text": msg.text or "",
                                    "date": msg.date.strftime("%m-%d %H:%M") if msg.date else "",
                                    "views": msg.views or 0,
                                    "has_media": msg.media is not None,
                                    "media_type": None,
                                    "thumb_key": None
                                }
                                
                                # 检测媒体类型并下载缩略图
                                if isinstance(msg.media, MessageMediaPhoto):
                                    msg_data["media_type"] = "photo"
                                    try:
                                        thumb_bytes = await client.download_media(msg.media, bytes, thumb=0)
                                        if thumb_bytes:
                                            thumb_img = Image.open(io.BytesIO(thumb_bytes)).convert("RGB")
                                            thumb_key = f"tg_{channel_username}_{msg.id}"
                                            telegram_thumbs[thumb_key] = thumb_img
                                            msg_data["thumb_key"] = thumb_key
                                    except Exception as e:
                                        logger.debug(f"下载图片缩略图失败: {e}")
                                        
                                elif isinstance(msg.media, MessageMediaDocument):
                                    is_video = False
                                    if msg.media.document:
                                        for attr in msg.media.document.attributes:
                                            if isinstance(attr, DocumentAttributeVideo):
                                                is_video = True
                                                break
                                    
                                    msg_data["media_type"] = "video" if is_video else "file"
                                    
                                    if msg.media.document and msg.media.document.thumbs:
                                        try:
                                            thumb_bytes = await client.download_media(msg.media, bytes, thumb=0)
                                            if thumb_bytes:
                                                thumb_img = Image.open(io.BytesIO(thumb_bytes)).convert("RGB")
                                                thumb_key = f"tg_{channel_username}_{msg.id}"
                                                telegram_thumbs[thumb_key] = thumb_img
                                                msg_data["thumb_key"] = thumb_key
                                        except Exception as e:
                                            logger.debug(f"下载视频缩略图失败: {e}")
                                
                                channel_data["messages"].append(msg_data)
                            
                            all_channel_data.append(channel_data)
                            
                        except Exception as e:
                            logger.error(f"获取频道 {channel_username} 失败: {e}")
                            all_channel_data.append({
                                "username": channel_username,
                                "title": channel_username,
                                "messages": [],
                                "error": str(e)[:30]
                            })
                    
                    # 更新数据
                    info["telegram_channel_data"] = all_channel_data
                    info["telegram_thumbs"] = telegram_thumbs
                    info["telegram_channels"] = channels
                    info["telegram_status"] = "Updated"
                    info["telegram_last_update"] = time.time()
                    logger.info(f"Telegram更新成功，获取到{len(all_channel_data)}个频道")
                    
                except Exception as e:
                    logger.error(f"获取Telegram消息失败: {e}")
                    info["telegram_status"] = f"Error: {str(e)[:20]}"
                    
                except Exception as e:
                    logger.error(f"获取Telegram消息失败: {e}")
                    info["telegram_status"] = f"Error: {str(e)[:20]}"
                
                await asyncio.sleep(TELEGRAM_UPDATE_INTERVAL)
                
        except Exception as e:
            logger.error(f"Telegram客户端错误: {e}")
            info["telegram_status"] = f"Client Error"
        finally:
            await client.disconnect()
    
    # 运行异步循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(fetch_messages())
    except Exception as e:
        logger.error(f"Telegram工作线程异常: {e}")
        info["telegram_status"] = "Thread Error"


def load_tracking_packages() -> List[Dict]:
    """从文件加载包裹列表"""
    try:
        if os.path.exists(TRACKING_DATA_FILE):
            with open(TRACKING_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"加载包裹数据失败: {e}")
    return []


def save_tracking_packages(packages: List[Dict]) -> None:
    """保存包裹列表到文件"""
    try:
        with open(TRACKING_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(packages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存包裹数据失败: {e}")


def query_tracking(tracking_number: str, carrier_code: str = None) -> Dict:
    """查询单个快递"""
    try:
        params = {"tracking_number": tracking_number}
        if carrier_code:
            params["carrier_code"] = carrier_code
        
        # 先尝试直接请求，失败则使用代理
        for use_proxy in [False, True]:
            try:
                resp = requests.get(
                    TRACKING_API_URL,
                    params=params,
                    timeout=15,
                    verify=False,
                    proxies=PROXIES if use_proxy else None
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    # 检查返回数据是否有效
                    if data and (data.get("tracks") or data.get("carrier_name")):
                        logger.info(f"物流查询成功 {tracking_number}: {data.get('carrier_name', '未知')}")
                        return data
                    else:
                        logger.warning(f"物流查询返回空数据 {tracking_number}: {resp.text[:200]}")
                else:
                    logger.warning(f"物流查询失败 {tracking_number}: HTTP {resp.status_code}, {resp.text[:200]}")
            except requests.RequestException as e:
                if not use_proxy:
                    logger.debug(f"直连失败，尝试代理: {e}")
                    continue
                raise
        
        return None
    except Exception as e:
        logger.error(f"物流查询异常 {tracking_number}: {e}")
        return None


def tracking_worker() -> None:
    """物流追踪工作线程"""
    # 已签收/领取的关键字，匹配到则自动剔除
    COMPLETED_KEYWORDS = [
        "已签收", "已领取", "已取件", "已收货", "签收成功",
        "代收点已签收", "已被签收", "本人签收", "他人签收",
        "已自提", "已取走", "派件已签收", "快件已签收"
    ]
    
    last_known_packages = set()  # 记录已知的包裹单号
    
    while True:
        try:
            # 检查是否需要强制更新
            force_update = info.get("tracking_force_update", False)
            if force_update:
                info["tracking_force_update"] = False
                logger.info("检测到新包裹，立即执行查询")
            
            # 加载包裹列表
            packages = load_tracking_packages()
            current_package_ids = set(p.get("tracking_number", "") for p in packages)
            
            if not packages:
                info["tracking_packages"] = []
                info["tracking_status"] = "无包裹"
                last_known_packages = set()
                time.sleep(30)
                continue
            
            # 检测是否有新包裹
            new_packages = current_package_ids - last_known_packages
            if new_packages:
                logger.info(f"检测到 {len(new_packages)} 个新包裹")
            last_known_packages = current_package_ids
            
            updated_packages = []
            packages_to_remove = []  # 需要自动删除的包裹
            
            for pkg in packages:
                tracking_number = pkg.get("tracking_number", "")
                carrier_code = pkg.get("carrier_code", "")
                alias = pkg.get("alias", "")
                
                if not tracking_number:
                    continue
                
                # 查询物流信息
                logger.info(f"正在查询物流: {tracking_number}")
                result = query_tracking(tracking_number, carrier_code)
                
                if result:
                    tracks = result.get("tracks", [])[:5]
                    
                    # 检查是否已签收/领取
                    is_completed = False
                    if tracks:
                        latest_track = tracks[0].get("context", "")
                        for keyword in COMPLETED_KEYWORDS:
                            if keyword in latest_track:
                                is_completed = True
                                logger.info(f"包裹 {tracking_number} 已签收，将自动移除")
                                packages_to_remove.append(tracking_number)
                                break
                    
                    # 如果未签收，添加到更新列表
                    if not is_completed:
                        updated_packages.append({
                            "tracking_number": tracking_number,
                            "alias": alias or result.get("carrier_name", "包裹"),
                            "carrier_name": result.get("carrier_name", "未知"),
                            "carrier_code": result.get("carrier_code", carrier_code),
                            "tracks": tracks,
                            "track_count": result.get("track_count", 0),
                            "last_update": time.time()
                        })
                else:
                    # 查询失败，保留基本信息
                    updated_packages.append({
                        "tracking_number": tracking_number,
                        "alias": alias or "包裹",
                        "carrier_name": pkg.get("carrier_name", "查询失败"),
                        "carrier_code": carrier_code,
                        "tracks": pkg.get("tracks", []),
                        "track_count": pkg.get("track_count", 0),
                        "last_update": pkg.get("last_update", 0)
                    })
                
                time.sleep(2)
            
            # 自动删除已签收的包裹
            if packages_to_remove:
                current_packages = load_tracking_packages()
                remaining = [p for p in current_packages if p.get("tracking_number") not in packages_to_remove]
                save_tracking_packages(remaining)
                last_known_packages -= set(packages_to_remove)
                logger.info(f"已自动移除 {len(packages_to_remove)} 个已签收包裹")
            
            info["tracking_packages"] = updated_packages
            info["tracking_status"] = f"已更新 {len(updated_packages)} 个"
            info["tracking_last_update"] = time.time()
            logger.info(f"物流数据更新完成，共 {len(updated_packages)} 个包裹")
            
        except Exception as e:
            logger.error(f"物流追踪线程异常: {e}")
            info["tracking_status"] = "更新失败"
        
        # 等待下次更新，但每秒检查是否有强制更新请求
        for _ in range(TRACKING_UPDATE_INTERVAL):
            if info.get("tracking_force_update", False):
                break
            time.sleep(1)


def load_bilibili_streamers() -> List[Dict]:
    """从文件加载主播列表"""
    try:
        if os.path.exists(BILIBILI_DATA_FILE):
            with open(BILIBILI_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"加载主播数据失败: {e}")
    return []


def save_bilibili_streamers(streamers: List[Dict]) -> None:
    """保存主播列表到文件"""
    try:
        with open(BILIBILI_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(streamers, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存主播数据失败: {e}")


def query_bilibili_live(mid: str = None, room_id: str = None) -> Dict:
    """查询B站直播间状态"""
    try:
        params = {}
        if mid:
            params["mid"] = mid
        elif room_id:
            params["room_id"] = room_id
        else:
            return None
        
        for use_proxy in [False, True]:
            try:
                resp = requests.get(
                    BILIBILI_LIVE_API_URL,
                    params=params,
                    timeout=15,
                    verify=False,
                    proxies=PROXIES if use_proxy else None
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data and data.get("uid"):
                        logger.info(f"B站直播查询成功: {data.get('title', '未知')[:20]}")
                        return data
                    else:
                        logger.warning(f"B站直播查询返回空数据: {resp.text[:200]}")
                else:
                    logger.warning(f"B站直播查询失败: HTTP {resp.status_code}")
            except requests.RequestException as e:
                if not use_proxy:
                    continue
                raise
        
        return None
    except Exception as e:
        logger.error(f"B站直播查询异常: {e}")
        return None


def load_saved_sessdata() -> str:
    """加载保存的SESSDATA"""
    try:
        if os.path.exists('/tmp/bili_sessdata.txt'):
            with open('/tmp/bili_sessdata.txt', 'r') as f:
                saved = f.read().strip()
                if saved:
                    return saved
    except:
        pass
    return BILIBILI_SESSDATA


def get_bilibili_headers() -> Dict:
    """获取B站API请求头"""
    sessdata = load_saved_sessdata()
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.bilibili.com",
        "Cookie": f"SESSDATA={sessdata}"
    }


def get_bilibili_user_info() -> Dict:
    """获取B站用户信息"""
    try:
        url = "https://api.bilibili.com/x/web-interface/nav"
        resp = requests.get(url, headers=get_bilibili_headers(), timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("code") == 0:
                d = data.get("data", {})
                return {
                    "uname": d.get("uname", ""),
                    "face": d.get("face", ""),
                    "level": d.get("level_info", {}).get("current_level", 0),
                    "coins": d.get("money", 0),
                    "bcoin": d.get("wallet", {}).get("bcoin_balance", 0),
                    "vip_type": d.get("vipType", 0),
                    "vip_label": d.get("vip", {}).get("label", {}).get("text", ""),
                    "follower": d.get("follower", 0)
                }
    except Exception as e:
        logger.error(f"获取B站用户信息失败: {e}")
    return {}


def bilibili_worker() -> None:
    """B站直播监控工作线程"""
    while True:
        try:
            streamers = load_bilibili_streamers()
            
            if not streamers:
                info["bilibili_streamers"] = []
                info["bilibili_status"] = "无主播"
                time.sleep(30)
                continue
            
            updated_streamers = []
            for streamer in streamers:
                mid = streamer.get("mid", "")
                room_id = streamer.get("room_id", "")
                alias = streamer.get("alias", "")
                
                if not mid and not room_id:
                    continue
                
                logger.info(f"正在查询B站主播: {mid or room_id}")
                result = query_bilibili_live(mid=mid, room_id=room_id)
                
                if result:
                    live_status = result.get("live_status", 0)
                    updated_streamers.append({
                        "mid": str(result.get("uid", mid)),
                        "room_id": str(result.get("room_id", room_id)),
                        "alias": alias,
                        "title": result.get("title", ""),
                        "live_status": live_status,
                        "online": result.get("online", 0),
                        "attention": result.get("attention", 0),
                        "area_name": result.get("area_name", ""),
                        "parent_area_name": result.get("parent_area_name", ""),
                        "user_cover": result.get("user_cover", ""),
                        "keyframe": result.get("keyframe", ""),
                        "live_time": result.get("live_time", ""),
                        "description": result.get("description", "")[:50],
                        "last_update": time.time()
                    })
                else:
                    streamer["live_status"] = streamer.get("live_status", -1)
                    streamer["last_update"] = streamer.get("last_update", 0)
                    updated_streamers.append(streamer)
                
                time.sleep(2)
            
            info["bilibili_streamers"] = updated_streamers
            info["bilibili_status"] = f"已更新 {len(updated_streamers)} 个"
            info["bilibili_last_update"] = time.time()
            
            # 检查是否有人开播
            live_count = sum(1 for s in updated_streamers if s.get("live_status") == 1)
            if live_count > 0:
                logger.info(f"B站直播: {live_count} 人正在直播")
            
        except Exception as e:
            logger.error(f"B站直播监控线程异常: {e}")
            info["bilibili_status"] = "更新失败"
        
        time.sleep(BILIBILI_UPDATE_INTERVAL)


def tracking_web_worker() -> None:
    """综合管理Web服务线程 - 物流+B站"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs
    
    class WebHandler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass
        
        def send_json(self, data, status=200):
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        
        def send_html(self, html):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        
        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            
            if path == '/' or path == '/index.html':
                self.send_html(WEB_MANAGER_HTML)
            
            # ===== 物流API =====
            elif path == '/api/packages':
                packages = load_tracking_packages()
                live_data = info.get("tracking_packages", [])
                live_map = {p["tracking_number"]: p for p in live_data}
                result_packages = []
                for pkg in packages:
                    tn = pkg["tracking_number"]
                    if tn in live_map:
                        result_packages.append(live_map[tn])
                    else:
                        pkg["carrier_name"] = pkg.get("carrier_name") or "识别中"
                        pkg["tracks"] = pkg.get("tracks", [])
                        result_packages.append(pkg)
                self.send_json({"packages": result_packages, "status": info.get("tracking_status", "")})
            
            elif path == '/api/packages/add':
                tn = query.get('tracking_number', [''])[0]
                alias = query.get('alias', [''])[0]
                carrier = query.get('carrier_code', [''])[0]
                if tn:
                    packages = load_tracking_packages()
                    exists = any(p["tracking_number"] == tn for p in packages)
                    if not exists:
                        packages.append({"tracking_number": tn, "alias": alias, "carrier_code": carrier})
                        save_tracking_packages(packages)
                        # 触发立即查询
                        info["tracking_force_update"] = True
                        self.send_json({"success": True, "message": "添加成功，正在查询..."})
                    else:
                        self.send_json({"success": False, "message": "单号已存在"})
                else:
                    self.send_json({"success": False, "message": "单号不能为空"}, 400)
            
            elif path == '/api/packages/delete':
                tn = query.get('tracking_number', [''])[0]
                if tn:
                    packages = load_tracking_packages()
                    packages = [p for p in packages if p["tracking_number"] != tn]
                    save_tracking_packages(packages)
                    self.send_json({"success": True, "message": "删除成功"})
                else:
                    self.send_json({"success": False, "message": "单号不能为空"}, 400)
            
            # ===== B站主播API =====
            elif path == '/api/streamers':
                streamers = load_bilibili_streamers()
                live_data = info.get("bilibili_streamers", [])
                live_map = {s.get("mid") or s.get("room_id"): s for s in live_data}
                result = []
                for s in streamers:
                    key = s.get("mid") or s.get("room_id")
                    if key in live_map:
                        result.append(live_map[key])
                    else:
                        s["live_status"] = s.get("live_status", -1)
                        result.append(s)
                self.send_json({"streamers": result, "status": info.get("bilibili_status", "")})
            
            elif path == '/api/streamers/add':
                mid = query.get('mid', [''])[0]
                room_id = query.get('room_id', [''])[0]
                alias = query.get('alias', [''])[0]
                if mid or room_id:
                    streamers = load_bilibili_streamers()
                    exists = any((s.get("mid") == mid and mid) or (s.get("room_id") == room_id and room_id) for s in streamers)
                    if not exists:
                        streamers.append({"mid": mid, "room_id": room_id, "alias": alias})
                        save_bilibili_streamers(streamers)
                        self.send_json({"success": True, "message": "添加成功"})
                    else:
                        self.send_json({"success": False, "message": "主播已存在"})
                else:
                    self.send_json({"success": False, "message": "请填写UID或房间号"}, 400)
            
            elif path == '/api/streamers/delete':
                mid = query.get('mid', [''])[0]
                room_id = query.get('room_id', [''])[0]
                streamers = load_bilibili_streamers()
                streamers = [s for s in streamers if not ((s.get("mid") == mid and mid) or (s.get("room_id") == room_id and room_id))]
                save_bilibili_streamers(streamers)
                self.send_json({"success": True, "message": "删除成功"})
            
            # ===== B站设置API =====
            elif path == '/api/bili/user':
                user = info.get("bilibili_user", {})
                self.send_json(user)
            
            elif path == '/api/bili/sessdata':
                global BILIBILI_SESSDATA
                new_sessdata = query.get('value', [''])[0]
                if new_sessdata:
                    BILIBILI_SESSDATA = new_sessdata
                    # 保存到文件
                    try:
                        with open('/tmp/bili_sessdata.txt', 'w') as f:
                            f.write(new_sessdata)
                    except:
                        pass
                    # 清空用户信息，触发重新获取
                    info["bilibili_user"] = {}
                    self.send_json({"success": True, "message": "SESSDATA已更新，将在下次刷新时生效"})
                else:
                    self.send_json({"success": False, "message": "SESSDATA不能为空"}, 400)
            
            # ===== Telegram频道API =====
            elif path == '/api/telegram/channels':
                channels = load_telegram_channels()
                current = info.get("telegram_channel_username", "")
                status = info.get("telegram_status", "")
                self.send_json({"channels": channels, "current": current, "status": status})
            
            elif path == '/api/telegram/channels/add':
                channel = query.get('channel', [''])[0].strip()
                if channel:
                    # 去掉@前缀
                    if channel.startswith('@'):
                        channel = channel[1:]
                    channels = load_telegram_channels()
                    if channel not in channels:
                        channels.append(channel)
                        save_telegram_channels(channels)
                        self.send_json({"success": True, "message": f"频道 @{channel} 添加成功"})
                    else:
                        self.send_json({"success": False, "message": "频道已存在"})
                else:
                    self.send_json({"success": False, "message": "频道名不能为空"}, 400)
            
            elif path == '/api/telegram/channels/delete':
                channel = query.get('channel', [''])[0].strip()
                if channel:
                    if channel.startswith('@'):
                        channel = channel[1:]
                    channels = load_telegram_channels()
                    if channel in channels:
                        channels.remove(channel)
                        save_telegram_channels(channels)
                        self.send_json({"success": True, "message": f"频道 @{channel} 已删除"})
                    else:
                        self.send_json({"success": False, "message": "频道不存在"})
                else:
                    self.send_json({"success": False, "message": "频道名不能为空"}, 400)
            
            elif path == '/api/telegram/config':
                config = load_telegram_config()
                # 隐藏部分api_hash
                api_hash = config.get("api_hash", "")
                if len(api_hash) > 8:
                    api_hash = api_hash[:4] + "****" + api_hash[-4:]
                self.send_json({
                    "api_id": config.get("api_id", 0),
                    "api_hash_masked": api_hash,
                    "configured": bool(config.get("api_id") and config.get("api_hash"))
                })
            
            elif path == '/api/telegram/config/save':
                api_id = query.get('api_id', [''])[0].strip()
                api_hash = query.get('api_hash', [''])[0].strip()
                if api_id and api_hash:
                    try:
                        api_id_int = int(api_id)
                        save_telegram_config(api_id_int, api_hash)
                        self.send_json({"success": True, "message": "Telegram API配置已保存，重启服务后生效"})
                    except ValueError:
                        self.send_json({"success": False, "message": "API ID必须是数字"}, 400)
                else:
                    self.send_json({"success": False, "message": "API ID和Hash不能为空"}, 400)
            
            else:
                self.send_response(404)
                self.end_headers()
        
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.end_headers()
    
    try:
        server = HTTPServer(('0.0.0.0', TRACKING_WEB_PORT), WebHandler)
        logger.info(f"综合管理Web服务已启动: http://0.0.0.0:{TRACKING_WEB_PORT}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"Web服务启动失败: {e}")


# 综合管理Web界面HTML
WEB_MANAGER_HTML = '''<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>屏幕管理中心</title>
    <style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0d1117;color:#c9d1d9;min-height:100vh;padding:16px}
        .container{max-width:900px;margin:0 auto}
        h1{color:#58a6ff;margin-bottom:16px;font-size:22px}
        .tabs{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap}
        .tab{padding:10px 20px;background:#21262d;border:1px solid #30363d;border-radius:6px;cursor:pointer;color:#8b949e}
        .tab.active{background:#238636;border-color:#238636;color:#fff}
        .tab.pink{background:#fb7299;border-color:#fb7299}
        .panel{display:none}
        .panel.active{display:block}
        .section{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:16px}
        .section-title{font-size:14px;color:#8b949e;margin-bottom:12px}
        .form-row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
        input,textarea{background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:10px 12px;color:#c9d1d9;font-size:14px;flex:1;min-width:120px}
        textarea{min-height:60px;resize:vertical}
        input:focus,textarea:focus{outline:none;border-color:#58a6ff}
        button{background:#238636;color:#fff;border:none;border-radius:6px;padding:10px 16px;cursor:pointer;font-size:14px}
        button:hover{background:#2ea043}
        button.secondary{background:#21262d}
        button.danger{background:#da3633;padding:6px 12px;font-size:12px}
        button.pink{background:#fb7299}
        button.pink:hover{background:#ff85a2}
        .list{display:flex;flex-direction:column;gap:10px}
        .card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px}
        .card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
        .card-title{font-weight:600;color:#58a6ff;font-size:15px}
        .card-subtitle{font-size:12px;color:#8b949e}
        .card-content{font-size:13px;color:#c9d1d9}
        .track{padding:6px 0;border-bottom:1px solid #21262d}
        .track:last-child{border-bottom:none}
        .track-time{color:#8b949e;font-size:11px}
        .status{text-align:center;color:#8b949e;padding:30px}
        .badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;margin-left:8px}
        .badge.live{background:#238636;color:#fff}
        .badge.offline{background:#30363d;color:#8b949e}
        .hint{font-size:12px;color:#8b949e;margin-top:8px}
        .success{color:#2ea043}
        .user-info{display:flex;gap:16px;align-items:center;padding:12px;background:#21262d;border-radius:6px;margin-bottom:12px}
        .user-info .name{font-weight:600;color:#fff}
        .user-info .level{background:#fb7299;padding:2px 8px;border-radius:4px;font-size:12px}
    </style>
</head>
<body>
    <div class="container">
        <h1>屏幕管理中心</h1>
        <div class="tabs">
            <div class="tab active" onclick="switchTab('tracking')">物流追踪</div>
            <div class="tab" onclick="switchTab('bilibili')">B站直播</div>
            <div class="tab" onclick="switchTab('telegram')">Telegram</div>
            <div class="tab" onclick="switchTab('settings')">设置</div>
        </div>
        
        <div id="tracking-panel" class="panel active">
            <div class="section">
                <div class="section-title">添加快递</div>
                <div class="form-row">
                    <input type="text" id="pkg-number" placeholder="快递单号">
                    <input type="text" id="pkg-alias" placeholder="备注名称" style="max-width:150px">
                    <input type="text" id="pkg-carrier" placeholder="快递编码" style="max-width:100px">
                    <button onclick="addPackage()">添加</button>
                    <button class="secondary" onclick="loadPackages()">刷新</button>
                </div>
            </div>
            <div class="list" id="packages-list"></div>
        </div>
        
        <div id="bilibili-panel" class="panel">
            <div class="section">
                <div class="section-title">添加主播 (UID和房间号填一个即可)</div>
                <div class="form-row">
                    <input type="text" id="streamer-mid" placeholder="用户UID">
                    <input type="text" id="streamer-room" placeholder="直播间号">
                    <input type="text" id="streamer-alias" placeholder="备注名称" style="max-width:150px">
                    <button class="pink" onclick="addStreamer()">添加</button>
                    <button class="secondary" onclick="loadStreamers()">刷新</button>
                </div>
            </div>
            <div class="list" id="streamers-list"></div>
        </div>
        
        <div id="telegram-panel" class="panel">
            <div class="section">
                <div class="section-title">Telegram API配置</div>
                <div id="tg-config-status" style="margin-bottom:8px"></div>
                <div class="form-row">
                    <input type="text" id="tg-api-id" placeholder="API ID (数字)">
                    <input type="text" id="tg-api-hash" placeholder="API Hash">
                    <button style="background:#0088cc" onclick="saveTgConfig()">保存</button>
                </div>
                <div class="hint">从 <a href="https://my.telegram.org" target="_blank" style="color:#58a6ff">my.telegram.org</a> 获取API ID和Hash，保存后需重启服务</div>
            </div>
            <div class="section">
                <div class="section-title">添加Telegram频道</div>
                <div class="form-row">
                    <input type="text" id="tg-channel" placeholder="频道用户名 (如 @Seele_WW_Leak 或 Seele_WW_Leak)">
                    <button style="background:#0088cc" onclick="addTgChannel()">添加</button>
                    <button class="secondary" onclick="loadTgChannels()">刷新</button>
                </div>
                <div class="hint">输入公开频道的用户名，可以带@也可以不带</div>
            </div>
            <div id="tg-status" style="margin-bottom:12px"></div>
            <div class="list" id="tg-channels-list"></div>
        </div>
        
        <div id="settings-panel" class="panel">
            <div class="section">
                <div class="section-title">B站账号设置</div>
                <div id="bili-user-info"></div>
                <div class="form-row">
                    <textarea id="sessdata" placeholder="输入SESSDATA (从浏览器Cookie获取)"></textarea>
                </div>
                <div class="form-row" style="margin-top:12px">
                    <button class="pink" onclick="saveSessdata()">保存SESSDATA</button>
                    <button class="secondary" onclick="loadBiliUser()">刷新状态</button>
                </div>
                <div class="hint">获取方法：登录B站 → F12开发者工具 → Application → Cookies → 复制SESSDATA的值</div>
            </div>
        </div>
    </div>
    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.querySelector(`.tab[onclick*="${tab}"]`).classList.add('active');
            document.getElementById(tab + '-panel').classList.add('active');
            if (tab === 'settings') loadBiliUser();
        }
        
        async function loadPackages() {
            try {
                const resp = await fetch('/api/packages');
                const data = await resp.json();
                renderPackages(data.packages || []);
            } catch (e) { document.getElementById('packages-list').innerHTML = '<div class="status">加载失败</div>'; }
        }
        
        function renderPackages(packages) {
            const el = document.getElementById('packages-list');
            if (!packages.length) { el.innerHTML = '<div class="status">暂无包裹</div>'; return; }
            el.innerHTML = packages.map(p => `
                <div class="card">
                    <div class="card-header">
                        <div>
                            <span class="card-title">${p.alias || p.carrier_name || '包裹'}</span>
                            <span class="card-subtitle">${p.tracking_number} · ${p.carrier_name || '识别中'}</span>
                        </div>
                        <button class="danger" onclick="deletePackage('${p.tracking_number}')">删除</button>
                    </div>
                    <div class="card-content">
                        ${(p.tracks||[]).slice(0,3).map(t => `<div class="track"><div class="track-time">${t.time||''}</div><div>${t.context||''}</div></div>`).join('') || '<div class="status">暂无物流信息</div>'}
                    </div>
                </div>
            `).join('');
        }
        
        async function addPackage() {
            const tn = document.getElementById('pkg-number').value.trim();
            const alias = document.getElementById('pkg-alias').value.trim();
            const carrier = document.getElementById('pkg-carrier').value.trim();
            if (!tn) { alert('请输入快递单号'); return; }
            try {
                const resp = await fetch(`/api/packages/add?tracking_number=${encodeURIComponent(tn)}&alias=${encodeURIComponent(alias)}&carrier_code=${encodeURIComponent(carrier)}`);
                const data = await resp.json();
                alert(data.message);
                if (data.success) { document.getElementById('pkg-number').value = ''; document.getElementById('pkg-alias').value = ''; loadPackages(); }
            } catch (e) { alert('添加失败'); }
        }
        
        async function deletePackage(tn) {
            if (!confirm('确定删除？')) return;
            await fetch(`/api/packages/delete?tracking_number=${encodeURIComponent(tn)}`);
            loadPackages();
        }
        
        async function loadStreamers() {
            try {
                const resp = await fetch('/api/streamers');
                const data = await resp.json();
                renderStreamers(data.streamers || []);
            } catch (e) { document.getElementById('streamers-list').innerHTML = '<div class="status">加载失败</div>'; }
        }
        
        function renderStreamers(streamers) {
            const el = document.getElementById('streamers-list');
            if (!streamers.length) { el.innerHTML = '<div class="status">暂无主播</div>'; return; }
            el.innerHTML = streamers.map(s => {
                const isLive = s.live_status === 1;
                const statusBadge = isLive ? '<span class="badge live">直播中</span>' : '<span class="badge offline">未开播</span>';
                const online = s.online ? `${(s.online/10000).toFixed(1)}万人` : '';
                return `
                <div class="card">
                    <div class="card-header">
                        <div>
                            <span class="card-title">${s.alias || s.title || '主播'}</span>${statusBadge}
                            <div class="card-subtitle">UID: ${s.mid || '-'} · 房间: ${s.room_id || '-'}</div>
                            ${isLive ? `<div style="margin-top:4px;color:#8b949e;font-size:12px">${s.area_name || ''} · ${online}</div>` : ''}
                        </div>
                        <button class="danger" onclick="deleteStreamer('${s.mid}','${s.room_id}')">删除</button>
                    </div>
                </div>
            `}).join('');
        }
        
        async function addStreamer() {
            const mid = document.getElementById('streamer-mid').value.trim();
            const room = document.getElementById('streamer-room').value.trim();
            const alias = document.getElementById('streamer-alias').value.trim();
            if (!mid && !room) { alert('请填写UID或房间号'); return; }
            try {
                const resp = await fetch(`/api/streamers/add?mid=${encodeURIComponent(mid)}&room_id=${encodeURIComponent(room)}&alias=${encodeURIComponent(alias)}`);
                const data = await resp.json();
                alert(data.message);
                if (data.success) { document.getElementById('streamer-mid').value = ''; document.getElementById('streamer-room').value = ''; document.getElementById('streamer-alias').value = ''; loadStreamers(); }
            } catch (e) { alert('添加失败'); }
        }
        
        async function deleteStreamer(mid, room) {
            if (!confirm('确定删除？')) return;
            await fetch(`/api/streamers/delete?mid=${encodeURIComponent(mid)}&room_id=${encodeURIComponent(room)}`);
            loadStreamers();
        }
        
        async function loadBiliUser() {
            try {
                const resp = await fetch('/api/bili/user');
                const data = await resp.json();
                const el = document.getElementById('bili-user-info');
                if (data.uname) {
                    el.innerHTML = `<div class="user-info"><span class="name">${data.uname}</span><span class="level">Lv${data.level}</span><span>硬币: ${data.coins}</span><span>B币: ${data.bcoin}</span></div>`;
                } else {
                    el.innerHTML = '<div class="user-info" style="color:#da3633">未登录或SESSDATA已过期</div>';
                }
            } catch (e) { document.getElementById('bili-user-info').innerHTML = '<div class="user-info" style="color:#da3633">获取失败</div>'; }
        }
        
        async function saveSessdata() {
            const sessdata = document.getElementById('sessdata').value.trim();
            if (!sessdata) { alert('请输入SESSDATA'); return; }
            try {
                const resp = await fetch(`/api/bili/sessdata?value=${encodeURIComponent(sessdata)}`);
                const data = await resp.json();
                alert(data.message);
                if (data.success) { document.getElementById('sessdata').value = ''; loadBiliUser(); }
            } catch (e) { alert('保存失败'); }
        }
        
        async function loadTgConfig() {
            try {
                const resp = await fetch('/api/telegram/config');
                const data = await resp.json();
                const el = document.getElementById('tg-config-status');
                if (data.configured) {
                    el.innerHTML = `<div style="color:#2ea043">已配置 · API ID: ${data.api_id} · Hash: ${data.api_hash_masked}</div>`;
                } else {
                    el.innerHTML = '<div style="color:#da3633">未配置 - 请填写API ID和Hash</div>';
                }
            } catch (e) { document.getElementById('tg-config-status').innerHTML = '<div style="color:#da3633">加载失败</div>'; }
        }
        
        async function saveTgConfig() {
            const apiId = document.getElementById('tg-api-id').value.trim();
            const apiHash = document.getElementById('tg-api-hash').value.trim();
            if (!apiId || !apiHash) { alert('请填写API ID和Hash'); return; }
            try {
                const resp = await fetch(`/api/telegram/config/save?api_id=${encodeURIComponent(apiId)}&api_hash=${encodeURIComponent(apiHash)}`);
                const data = await resp.json();
                alert(data.message);
                if (data.success) { 
                    document.getElementById('tg-api-id').value = ''; 
                    document.getElementById('tg-api-hash').value = ''; 
                    loadTgConfig(); 
                }
            } catch (e) { alert('保存失败'); }
        }
        
        async function loadTgChannels() {
            try {
                const resp = await fetch('/api/telegram/channels');
                const data = await resp.json();
                document.getElementById('tg-status').innerHTML = `<div style="color:#8b949e;font-size:13px">状态: ${data.status || '未知'} · 当前频道: @${data.current || '-'}</div>`;
                renderTgChannels(data.channels || []);
            } catch (e) { document.getElementById('tg-channels-list').innerHTML = '<div class="status">加载失败</div>'; }
        }
        
        function renderTgChannels(channels) {
            const el = document.getElementById('tg-channels-list');
            if (!channels.length) { el.innerHTML = '<div class="status">暂无频道</div>'; return; }
            el.innerHTML = channels.map(c => `
                <div class="card">
                    <div class="card-header">
                        <div>
                            <span class="card-title" style="color:#0088cc">@${c}</span>
                            <span class="card-subtitle">t.me/${c}</span>
                        </div>
                        <button class="danger" onclick="deleteTgChannel('${c}')">删除</button>
                    </div>
                </div>
            `).join('');
        }
        
        async function addTgChannel() {
            const channel = document.getElementById('tg-channel').value.trim();
            if (!channel) { alert('请输入频道用户名'); return; }
            try {
                const resp = await fetch(`/api/telegram/channels/add?channel=${encodeURIComponent(channel)}`);
                const data = await resp.json();
                alert(data.message);
                if (data.success) { document.getElementById('tg-channel').value = ''; loadTgChannels(); }
            } catch (e) { alert('添加失败'); }
        }
        
        async function deleteTgChannel(channel) {
            if (!confirm('确定删除频道 @' + channel + '？')) return;
            await fetch(`/api/telegram/channels/delete?channel=${encodeURIComponent(channel)}`);
            loadTgChannels();
        }
        
        loadPackages();
        loadStreamers();
        loadTgChannels();
        loadTgConfig();
    </script>
</body>
</html>'''


def control_worker() -> None:
    """远程控制工作线程"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind(("0.0.0.0", CONTROL_UDP_PORT))
            sock.settimeout(1.0)
            logger.info(f"远程控制监听已启动，端口: {CONTROL_UDP_PORT}")
            logger.info("发送 'next' 可以切换页面")
            
            while True:
                try:
                    data, addr = sock.recvfrom(1024)
                    cmd = data.decode('utf-8', errors='ignore').strip().lower()
                    
                    if cmd == "next":
                        old_page = button_state.get_page()
                        button_state.next_page()
                        new_page = button_state.get_page()
                        logger.info(f"远程页面切换: {old_page} -> {new_page} (来自 {addr[0]})")
                        
                        # 发送确认回复
                        response = f"页面切换到 {new_page}"
                        sock.sendto(response.encode('utf-8'), addr)
                        
                    elif cmd == "status":
                        current_page = button_state.get_page()
                        response = f"当前页面: {current_page}"
                        sock.sendto(response.encode('utf-8'), addr)
                        
                    else:
                        response = "支持的命令: next, status"
                        sock.sendto(response.encode('utf-8'), addr)
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.debug(f"控制命令处理异常: {e}")
                    
    except Exception as e:
        logger.error(f"远程控制线程异常: {e}")
        time.sleep(5)

# ================= 4. 按键处理 =================
class ButtonState:
    """简化的按键状态管理"""
    def __init__(self):
        self._lock = threading.Lock()
        self.current_page = 0
        self.page_locked = False
    
    def get_page(self) -> int:
        with self._lock:
            return self.current_page
    
    def next_page(self) -> None:
        with self._lock:
            if self.page_locked:
                logger.warning("页面已锁定，忽略切换请求")
                return
            old_page = self.current_page
            self.current_page = (self.current_page + 1) % MAX_PAGES
            logger.info(f"页面切换: {old_page} -> {self.current_page}")
    
    def unlock_pages(self) -> None:
        with self._lock:
            self.page_locked = False
            logger.info("页面切换已解锁")
    
    def lock_pages(self) -> None:
        with self._lock:
            self.page_locked = True
            logger.info("页面切换已锁定")
    
    def is_screen_on(self) -> bool:
        return True


button_state = ButtonState()


class ButtonManager:
    """全新的按钮管理器 - 更稳定的实现"""
    def __init__(self):
        self.last_state = False
        self.last_change_time = 0
        self.press_start_time = 0
        self.is_pressing = False
        self.initialized = False
        
    def init_button(self) -> bool:
        """初始化按钮GPIO"""
        try:
            if not init_button_gpio():
                logger.error("按钮GPIO初始化失败")
                return False
            
            # 读取初始状态并稳定化
            initial_readings = []
            for _ in range(20):
                initial_readings.append(read_button_raw())
                time.sleep(0.01)
            
            # 统计初始状态
            pressed_count = sum(initial_readings)
            logger.info(f"按钮初始状态: {pressed_count}/20 次检测到按下")
            
            if pressed_count > 15:
                logger.error("按钮可能短路或卡住，禁用按钮功能")
                return False
            elif pressed_count > 5:
                logger.warning("按钮状态不稳定，可能有硬件问题")
            
            self.last_state = pressed_count > 10  # 如果超过一半时间是按下状态，认为初始是按下的
            self.last_change_time = time.time()
            self.initialized = True
            logger.info("按钮初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"按钮初始化异常: {e}")
            return False
    
    def read_stable_state(self) -> bool:
        """读取稳定的按钮状态"""
        if not self.initialized:
            return False
            
        try:
            # 快速采样多次
            samples = []
            for _ in range(5):
                samples.append(read_button_raw())
                time.sleep(BUTTON_SAMPLE_INTERVAL)
            
            # 取多数决定
            pressed_count = sum(samples)
            return pressed_count >= 3  # 5次中至少3次为True
            
        except Exception as e:
            logger.debug(f"读取按钮状态失败: {e}")
            return False
    
    def update(self) -> bool:
        """更新按钮状态，返回是否有有效按键事件"""
        if not self.initialized:
            return False
            
        current_time = time.time()
        current_state = self.read_stable_state()
        
        # 检查状态变化
        if current_state != self.last_state:
            # 防抖：必须经过足够的时间间隔
            if current_time - self.last_change_time < BUTTON_DEBOUNCE_TIME:
                return False
            
            self.last_change_time = current_time
            
            if current_state:  # 按下
                if not self.is_pressing:
                    self.is_pressing = True
                    self.press_start_time = current_time
                    logger.info("按钮按下")
            else:  # 释放
                if self.is_pressing:
                    press_duration = current_time - self.press_start_time
                    self.is_pressing = False
                    
                    logger.info(f"按钮释放，持续时间: {press_duration:.3f}s")
                    
                    # 检查是否为有效按压
                    if press_duration >= BUTTON_MIN_PRESS_TIME:
                        logger.info("检测到有效按键")
                        self.last_state = current_state
                        return True
            
            self.last_state = current_state
        
        return False


button_manager = ButtonManager()


def button_monitor_strict() -> None:
    """按钮监控 - PC6引脚极速版"""
    if not init_button_gpio():
        logger.error("按钮GPIO初始化失败")
        return
    
    logger.info("按钮监控已启动（极速模式）")
    
    # 获取页面函数引用
    # 页面顺序: 时钟 -> 物流追踪 -> B站 -> 加密货币 -> 日历 -> Beszel -> Telegram
    page_functions = [draw_clock, draw_tracking, draw_bilibili, draw_crypto, draw_calendar, draw_beszel, draw_telegram]
    
    last_switch_time = 0
    MIN_SWITCH_INTERVAL = 0.3
    
    while True:
        try:
            # 等待按钮按下
            while True:
                samples = [read_button_raw() for _ in range(3)]
                if sum(samples) >= 2:
                    break
                time.sleep(0.005)
            
            press_time = time.time()
            logger.info(f"按钮按下")
            
            # 等待按钮释放
            while True:
                samples = [read_button_raw() for _ in range(3)]
                if sum(samples) <= 1:
                    break
                time.sleep(0.005)
            
            logger.info(f"按钮释放")
            
            # 检查切换间隔并切换页面
            current_time = time.time()
            if current_time - last_switch_time >= MIN_SWITCH_INTERVAL:
                button_state.next_page()
                last_switch_time = current_time
            
            time.sleep(0.02)
            
        except Exception as e:
            logger.error(f"按钮监控异常: {e}")
            time.sleep(0.1)


# ================= 5. 绘图函数 =================
# 字体初始化
font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
# 优先尝试容器内预备的字体路径，如果不存在则回退
if not os.path.exists(font_path):
    font_path = os.path.join(BASE_DIR, "fonts", "wqy-zenhei.ttc")
    if not os.path.exists(font_path):
        # 最后的兜底：通用的 Linux 中文字体路径
        font_path = "/usr/share/fonts/truetype/wqy-zenhei/wqy-zenhei.ttc"

nixie_font_path = os.path.join(BASE_DIR, "fonts", "reNix-Regular.otf")

try:
    f_nixie = ImageFont.truetype(font_path, 65) 
    f_asset_lg = ImageFont.truetype(font_path, 45)
    f_asset_md = ImageFont.truetype(font_path, 32)
    f_asset = ImageFont.truetype(font_path, 22)
    f_date, f_lunar, f_big, f_mid, f_sm, f_tiny = [
        ImageFont.truetype(font_path, size)
        for size in [18, 14, 60, 20, 15, 11]
    ]
    logger.info("中文字体加载成功")
except Exception as e:
    logger.error(f"中文字体加载失败: {e}，使用默认字体")
    f_nixie = f_asset_lg = f_asset_md = f_asset = f_date = f_lunar = f_big = f_mid = f_sm = f_tiny = ImageFont.load_default()

# reNix 辉光管字体
try:
    f_renix_big = ImageFont.truetype(nixie_font_path, 78)
    f_renix_small = ImageFont.truetype(nixie_font_path, 24)
    logger.info("reNix 字体加载成功")
except Exception as e:
    logger.warning(f"reNix 字体加载失败: {e}，使用备用字体")
    f_renix_big = f_nixie
    f_renix_small = f_sm


def is_night_mode() -> bool:
    """判断是否为夜间模式 (01:30-08:00)"""
    now = datetime.now()
    current_minutes = now.hour * 60 + now.minute
    start_minutes = NIGHT_MODE_START_HOUR * 60 + NIGHT_MODE_START_MINUTE
    end_minutes = NIGHT_MODE_END_HOUR * 60 + NIGHT_MODE_END_MINUTE
    return start_minutes <= current_minutes < end_minutes


def adjust_brightness(img: Image.Image, factor: float) -> Image.Image:
    """调整图像亮度"""
    return ImageEnhance.Brightness(img).enhance(factor)


def draw_centered_text(draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont, y: int, color: Tuple[int, int, int]) -> None:
    """绘制居中文本"""
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    x = (W - text_width) // 2
    draw.text((x, y), text, fill=color, font=font)


def get_time_based_colors() -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
    """根据时间返回动态色调 (背景主色, 背景副色, 装饰色)"""
    hour = datetime.now().hour
    
    if 5 <= hour < 8:  # 清晨 - 淡橙暖色
        return (22, 18, 28), (28, 22, 18), (80, 60, 40)
    elif 8 <= hour < 12:  # 上午 - 清新蓝绿
        return (15, 20, 28), (18, 25, 32), (40, 70, 80)
    elif 12 <= hour < 17:  # 下午 - 明亮蓝
        return (16, 22, 32), (20, 26, 38), (50, 80, 100)
    elif 17 <= hour < 20:  # 傍晚 - 暖橙紫
        return (25, 18, 25), (30, 20, 28), (90, 60, 70)
    elif 20 <= hour < 23:  # 夜晚 - 深蓝紫
        return (18, 16, 28), (22, 18, 35), (60, 50, 90)
    else:  # 深夜 - 深邃蓝黑
        return (12, 14, 22), (15, 16, 26), (40, 45, 70)


def create_dynamic_background(width: int = W, height: int = H) -> Image.Image:
    """创建带时间动态色调的背景"""
    bg_top, bg_bottom, accent = get_time_based_colors()
    
    img = Image.new("RGB", (width, height), bg_top)
    draw = ImageDraw.Draw(img)
    
    # 垂直渐变
    for y in range(height):
        ratio = y / height
        r = int(bg_top[0] * (1 - ratio) + bg_bottom[0] * ratio)
        g = int(bg_top[1] * (1 - ratio) + bg_bottom[1] * ratio)
        b = int(bg_top[2] * (1 - ratio) + bg_bottom[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return img


# ================= 公共绘图工具函数 =================

def calc_text_width(text: str) -> int:
    """计算文本像素宽度（中文约10px，英文约6px）"""
    return sum(UI_CHAR_WIDTH_CN if ord(c) > 127 else UI_CHAR_WIDTH_EN for c in text)


def truncate_text(text: str, max_width: int, ellipsis: str = "..") -> str:
    """按像素宽度截断文字"""
    if calc_text_width(text) <= max_width:
        return text
    
    ellipsis_w = calc_text_width(ellipsis)
    result = ""
    current_w = 0
    
    for c in text:
        char_w = UI_CHAR_WIDTH_CN if ord(c) > 127 else UI_CHAR_WIDTH_EN
        if current_w + char_w + ellipsis_w > max_width:
            return result + ellipsis
        result += c
        current_w += char_w
    
    return result


def draw_page_header(draw: ImageDraw.Draw, title: str, accent_color: Tuple[int, int, int], 
                     right_text: str = None, height: int = UI_HEADER_HEIGHT) -> None:
    """绘制页面标题栏"""
    bg_top, _, _ = get_time_based_colors()
    
    # 标题栏背景
    draw.rectangle([0, 0, W, height], fill=(bg_top[0] + 10, bg_top[1] + 12, bg_top[2] + 18))
    # 底部强调线
    draw.rectangle([0, height - 2, W, height], fill=accent_color)
    
    # 标题文字
    draw.text((UI_PADDING + 2, (height - 12) // 2), title, (220, 230, 245), f_sm)
    
    # 右侧文字（如时间）
    if right_text:
        right_w = calc_text_width(right_text)
        draw.text((W - right_w - UI_PADDING - 2, (height - 10) // 2), right_text, (120, 140, 170), f_tiny)


def draw_status_bar(draw: ImageDraw.Draw, items: List[Tuple[str, Tuple[int, int, int]]], 
                    y: int = None) -> None:
    """绘制底部状态栏
    items: [(文字, 颜色), ...]
    """
    if y is None:
        y = H - UI_FOOTER_HEIGHT
    
    bg_top, _, accent = get_time_based_colors()
    
    # 背景
    draw.rectangle([0, y, W, H], fill=(bg_top[0] + 5, bg_top[1] + 6, bg_top[2] + 8))
    draw.line([0, y, W, y], fill=(accent[0] + 20, accent[1] + 30, accent[2] + 40))
    
    # 均分显示各项
    if not items:
        return
    
    section_w = W // len(items)
    text_y = y + (UI_FOOTER_HEIGHT - 10) // 2
    
    for i, (text, color) in enumerate(items):
        x = i * section_w + UI_PADDING
        draw.text((x, text_y), text, color, f_tiny)


def draw_card(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int, 
              fill: Tuple[int, int, int] = None, outline: Tuple[int, int, int] = None,
              radius: int = UI_CARD_RADIUS) -> None:
    """绘制圆角卡片"""
    bg_top, _, _ = get_time_based_colors()
    if fill is None:
        fill = (bg_top[0] + 8, bg_top[1] + 10, bg_top[2] + 14)
    
    draw.rounded_rectangle([x, y, x + w, y + h], radius, fill=fill, outline=outline)


def get_clothing_advice(category: str) -> str:
    """根据天气类别获取穿衣建议"""
    advice_map = {
        "寒冷": "寒冷|添衣",
        "冷": "天冷|保暖",
        "凉": "转凉|加衣",
        "舒适": "舒适|宜行",
        "热": "天热|防晒",
        "炎热": "炎热|防暑",
        "雨": "带伞|防雨"
    }
    return advice_map.get(category, f"衣:{category}")

# >>> 重新设计：天气/信息卡片 (整合当前天气) <<<
def get_weather_color(text: str) -> Tuple[int, int, int]:
    """根据天气文本获取颜色"""
    if "雨" in text:
        return (100, 180, 255)
    elif "晴" in text:
        return (255, 200, 50)
    else:
        return (220, 220, 230)


def get_aqi_color(aqi_str: str) -> Tuple[int, int, int]:
    """根据AQI值获取颜色"""
    try:
        aqi_val = int(aqi_str)
        if aqi_val <= 50:
            return (50, 200, 100)  # 绿色
        elif aqi_val <= 100:
            return (220, 200, 50)  # 黄色
        else:
            return (255, 80, 80)   # 红色
    except (ValueError, TypeError):
        return (150, 150, 150)  # 灰色


def clean_log_message(raw_log: str) -> str:
    """清理日志消息（去除Emoji等）"""
    # 提取消息部分
    msg = raw_log.split(" - ")[-1] if " - " in raw_log else raw_log
    # 过滤Emoji（保留基本多文种平面字符）
    clean_msg = re.sub(r'[^\u0000-\uFFFF]', '', msg).strip()
    # 如果过滤后为空，使用原始消息的前15个字符
    return clean_msg if clean_msg else raw_log[:15]


def get_wind_direction_text(wind_dir: str) -> str:
    """将风向代码转换为简短文本"""
    wind_map = {
        "N": "北", "NNE": "北", "NE": "东北", "ENE": "东北",
        "E": "东", "ESE": "东", "SE": "东南", "SSE": "东南",
        "S": "南", "SSW": "南", "SW": "西南", "WSW": "西南",
        "W": "西", "WNW": "西", "NW": "西北", "NNW": "西北"
    }
    return wind_map.get(wind_dir.upper(), wind_dir[:2])


def draw_weather_icon(draw: ImageDraw.Draw, x: int, y: int, size: int, weather: str, frame: int = 0) -> None:
    """绘制动态天气图标"""
    cx, cy = x + size // 2, y + size // 2
    
    if "晴" in weather:
        # 太阳 - 带旋转光芒动效
        sun_color = (255, 200, 80)
        ray_color = (255, 180, 60)
        # 太阳主体
        r = size // 3
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=sun_color)
        # 光芒（根据frame旋转）
        import math
        for i in range(8):
            angle = math.radians(i * 45 + frame * 3)
            x1 = cx + int(math.cos(angle) * (r + 3))
            y1 = cy + int(math.sin(angle) * (r + 3))
            x2 = cx + int(math.cos(angle) * (r + 8))
            y2 = cy + int(math.sin(angle) * (r + 8))
            draw.line([x1, y1, x2, y2], fill=ray_color, width=2)
    
    elif "雨" in weather:
        # 云+雨滴
        cloud_color = (120, 140, 160)
        rain_color = (100, 180, 255)
        # 云
        draw.ellipse([cx - 12, cy - 8, cx + 2, cy + 4], fill=cloud_color)
        draw.ellipse([cx - 4, cy - 12, cx + 12, cy + 2], fill=cloud_color)
        draw.ellipse([cx + 2, cy - 6, cx + 14, cy + 4], fill=cloud_color)
        # 雨滴（动态下落）
        drop_offset = (frame * 2) % 10
        for i, dx in enumerate([-6, 2, 10]):
            dy = (drop_offset + i * 3) % 10
            draw.line([cx + dx, cy + 6 + dy, cx + dx - 2, cy + 12 + dy], fill=rain_color, width=2)
    
    elif "云" in weather or "阴" in weather:
        # 云朵
        cloud_color = (150, 160, 175)
        cloud_dark = (120, 130, 145)
        # 主云
        draw.ellipse([cx - 14, cy - 4, cx + 2, cy + 10], fill=cloud_color)
        draw.ellipse([cx - 6, cy - 10, cx + 10, cy + 6], fill=cloud_color)
        draw.ellipse([cx + 2, cy - 2, cx + 16, cy + 10], fill=cloud_dark)
    
    elif "雪" in weather:
        # 雪花
        snow_color = (220, 230, 255)
        import math
        # 雪花图案
        for i in range(6):
            angle = math.radians(i * 60 + frame * 2)
            x1 = cx + int(math.cos(angle) * 4)
            y1 = cy + int(math.sin(angle) * 4)
            x2 = cx + int(math.cos(angle) * 10)
            y2 = cy + int(math.sin(angle) * 10)
            draw.line([x1, y1, x2, y2], fill=snow_color, width=1)
        draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=snow_color)
    
    else:
        # 默认：小太阳
        draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(200, 180, 100))


def draw_weather_card_enhanced(draw: ImageDraw.Draw, x: int, y: int, width: int, height: int, night: bool) -> None:
    """绘制简洁美观的天气卡片"""
    # 卡片背景
    bg_color = (18, 22, 30)
    draw.rounded_rectangle([x, y, x + width, y + height], 6, fill=bg_color)
    
    # 左侧渐变装饰条
    for i in range(4):
        alpha = 1 - i * 0.25
        color = (int(80 * alpha), int(160 * alpha), int(220 * alpha))
        draw.rectangle([x + i, y + 4, x + i + 1, y + height - 4], fill=color)
    
    if not info.get("forecast"):
        draw.text((x + 20, y + 18), "加载中...", (100, 110, 130), f_sm)
        return
    
    weather_text = info.get('text', '...')
    temp = info.get('temp', '--')
    
    # 动态帧（基于秒数）
    frame = int(time.time() * 2) % 60
    
    # 左侧：天气图标
    icon_x = x + 10
    icon_y = y + 8
    draw_weather_icon(draw, icon_x, icon_y, 32, weather_text, frame)
    
    # 中间：温度（大号）
    temp_str = f"{temp}°"
    draw.text((x + 48, y + 4), temp_str, (255, 255, 255), f_mid)
    
    # 温度下方：天气描述
    draw.text((x + 48, y + 26), weather_text, (180, 190, 210), f_tiny)
    
    # 右侧：AQI
    aqi_val = info.get('aqi', '0')
    aqi_color = get_aqi_color(aqi_val)
    try:
        aqi_num = int(aqi_val)
        aqi_status = "优" if aqi_num <= 50 else "良" if aqi_num <= 100 else "中" if aqi_num <= 150 else "差"
    except:
        aqi_status = ""
    
    # AQI 小标签
    aqi_x = x + width - 38
    aqi_y = y + 6
    # 背景色块
    aqi_bg = (aqi_color[0] // 4, aqi_color[1] // 4, aqi_color[2] // 4)
    draw.rounded_rectangle([aqi_x, aqi_y, aqi_x + 32, aqi_y + 16], 3, fill=aqi_bg)
    draw.text((aqi_x + 4, aqi_y + 2), f"{aqi_status}{aqi_val}", aqi_color, f_tiny)
    
    # 右下角：明日预报
    if len(info.get("forecast", [])) > 1:
        tomorrow = info["forecast"][1]
        tom_text = f"明日{tomorrow.get('tempMin', '')}~{tomorrow.get('tempMax', '')}°"
        tom_bbox = draw.textbbox((0, 0), tom_text, f_tiny)
        tom_w = tom_bbox[2] - tom_bbox[0]
        draw.text((x + width - tom_w - 6, y + height - 14), tom_text, (120, 130, 150), f_tiny)


def draw_forecast_cards(draw: ImageDraw.Draw, y_s: int, night: bool) -> None:
    """绘制天气和系统监控卡片"""
    card_width, card_height, gap = 140, 50, 10
    start_x = (W - (card_width * 2 + gap)) // 2
    
    # 左侧卡片：天气信息
    left_x = start_x
    draw_weather_card_enhanced(draw, left_x, y_s, card_width, card_height, night)
    
    # 右侧卡片：系统监控（重构版）
    right_x = start_x + card_width + gap
    draw_system_card(draw, right_x, y_s, card_width, card_height)


def draw_system_card(draw: ImageDraw.Draw, x: int, y: int, width: int, height: int) -> None:
    """绘制系统监控卡片 - 简洁美观版"""
    # 卡片背景
    bg_color = (18, 22, 30)
    draw.rounded_rectangle([x, y, x + width, y + height], 6, fill=bg_color)
    
    # 右侧渐变装饰条
    for i in range(3):
        alpha = 1 - i * 0.3
        color = (int(80 * alpha), int(180 * alpha), int(130 * alpha))
        draw.rectangle([x + width - 3 + i, y + 4, x + width - 2 + i, y + height - 4], fill=color)
    
    # 获取系统数据
    cpu_temp = info.get('cpu_t', 0)
    cpu_usage = int(info.get('cpu_u', 0))
    ram_usage = int(info.get('ram', 0))
    disk_usage = int(info.get('disk', 0))
    
    # 左上：温度
    temp_color = (255, 100, 100) if cpu_temp > 70 else (255, 200, 100) if cpu_temp > 55 else (100, 200, 150)
    draw.text((x + 6, y + 4), f"{cpu_temp}°C", temp_color, f_sm)
    
    # 右上：运行时间
    uptime = info.get('uptime', '0天0时')
    up_bbox = draw.textbbox((0, 0), uptime, f_tiny)
    up_w = up_bbox[2] - up_bbox[0]
    draw.text((x + width - up_w - 8, y + 6), uptime, (120, 130, 150), f_tiny)
    
    # 中间：三个迷你进度条（横向排列）
    bar_y = y + 24
    bar_h = 8
    bar_w = 28
    labels = ["C", "R", "D"]
    values = [cpu_usage, ram_usage, disk_usage]
    colors = [(100, 180, 255), (180, 130, 255), (100, 200, 150)]
    
    for i in range(3):
        # 每个指标的起始x位置
        bx = x + 6 + i * 42
        
        # 标签
        draw.text((bx, bar_y), labels[i], (130, 140, 160), f_tiny)
        
        # 进度条背景
        pbx = bx + 12
        draw.rounded_rectangle([pbx, bar_y + 1, pbx + bar_w, bar_y + 1 + bar_h], 2, fill=(35, 40, 50))
        
        # 进度条填充
        value = values[i]
        fill_w = max(2, int(bar_w * min(value, 100) / 100))
        if value > 80:
            fill_color = (255, 100, 100)
        elif value > 60:
            fill_color = (255, 200, 100)
        else:
            fill_color = colors[i]
        
        if fill_w > 2:
            draw.rounded_rectangle([pbx, bar_y + 1, pbx + fill_w, bar_y + 1 + bar_h], 2, fill=fill_color)
    
    # 底部：数值
    val_y = y + height - 13
    draw.text((x + 8, val_y), f"{cpu_usage}%", (140, 150, 170), f_tiny)
    draw.text((x + 52, val_y), f"{ram_usage}%", (140, 150, 170), f_tiny)
    draw.text((x + 96, val_y), f"{disk_usage}%", (140, 150, 170), f_tiny)

        
def draw_premium_bg(draw: ImageDraw.Draw, tube_centers: List[Tuple[int, int]]) -> None:
    """绘制高级背景效果 - 包含光晕、渐变和纹理"""
    # 深色渐变背景
    bg_dark = (8, 8, 10)
    bg_medium = (12, 12, 15)
    bg_light = (18, 18, 22)
    
    # 顶部较暗
    draw.rectangle([0, 0, W, H // 3], fill=bg_dark)
    # 中间（辉光管区域）
    draw.rectangle([0, H // 3, W, 2 * H // 3], fill=bg_medium)
    # 底部较亮
    draw.rectangle([0, 2 * H // 3, W, H], fill=bg_light)
    
    # 细节点阵纹理（降低密度，更精致）
    dot_color = (20, 20, 24)
    for x in range(0, W, 8):
        for y in range(0, H, 8):
            if (x + y) % 16 < 8:  # 棋盘模式
                draw.point((x, y), fill=dot_color)
    
    # 为每个辉光管添加环境光晕（仅轻微效果，避免黑色圆圈）
    for center_x, center_y in tube_centers:
        # 只绘制轻微的背景光晕，减少层数和范围
        for radius, alpha_mult in [(30, 0.12), (20, 0.08)]:
            alpha = alpha_mult
            glow_color = tuple(int(c * alpha) for c in (255, 140, 50))
            # 只绘制2层，避免产生黑色圆圈
            for i in range(2, 0, -1):
                alpha_factor = i / 2 * alpha
                glow = tuple(int(c * alpha_factor) for c in glow_color)
                glow_r = radius + i * 2
                # 确保颜色不会太暗
                if min(glow) < 5:  # 如果颜色太暗，跳过
                    continue
                draw.ellipse(
                    [center_x - glow_r, center_y - glow_r, center_x + glow_r, center_y + glow_r],
                    fill=glow,
                    outline=None
                )
    
    # 精致底座（带渐变和阴影）
    base_x, base_y, base_w, base_h = 25, 138, 270, 12
    # 底座阴影
    draw.rounded_rectangle(
        [base_x + 2, base_y + 2, base_x + base_w + 2, base_y + base_h + 2],
        radius=6,
        fill=(5, 5, 8)
    )
    # 底座主体
    draw.rounded_rectangle(
        [base_x, base_y, base_x + base_w, base_y + base_h],
        radius=6,
        fill=(25, 25, 32),
        outline=(45, 45, 55),
        width=2
    )
    # 底座高光
    draw.line(
        [base_x + 5, base_y + 2, base_x + base_w - 5, base_y + 2],
        fill=(50, 50, 60),
        width=1
    )
    
    # 顶部装饰线条
    draw.line([10, 25, W - 10, 25], fill=(30, 30, 38), width=1)
    draw.line([10, 27, W - 10, 27], fill=(20, 20, 28), width=1)

def draw_glow_effect(draw: ImageDraw.Draw, x: int, y: int, radius: int, color: Tuple[int, int, int], intensity: int = 5) -> None:
    """绘制发光效果（通过多个同心圆模拟）"""
    r, g, b = color
    for i in range(intensity, 0, -1):
        alpha_factor = i / intensity * 0.3
        glow_color = (
            int(r * alpha_factor),
            int(g * alpha_factor),
            int(b * alpha_factor)
        )
        glow_radius = radius + i * 2
        draw.ellipse(
            [x - glow_radius, y - glow_radius, x + glow_radius, y + glow_radius],
            fill=glow_color,
            outline=None
        )


def draw_clock() -> Image.Image:
    """绘制 Nixie 管风格时钟页面 - 使用素材图片版"""
    now = datetime.now()
    night = is_night_mode()
    
    # 极深黑背景
    img = Image.new("RGB", (W, H), (5, 5, 8))
    draw = ImageDraw.Draw(img)
    
    # 获取时间色调
    bg_top, _, accent = get_time_based_colors()
    
    # ========== 1. 顶部信息栏 ==========
    header_h = 28
    
    # 顶部渐变背景
    for hy in range(header_h):
        alpha = hy / header_h
        r = int(15 * (1 - alpha) + 8 * alpha)
        g = int(18 * (1 - alpha) + 10 * alpha)
        b = int(25 * (1 - alpha) + 15 * alpha)
        draw.rectangle([0, hy, W, hy + 1], fill=(r, g, b))
    
    # 底部发光线
    draw.rectangle([0, header_h - 2, W, header_h - 1], fill=(50, 80, 120))
    draw.rectangle([0, header_h - 1, W, header_h], fill=(25, 40, 60))
    
    # 左侧：模式标识
    mode_text = "NIGHT" if night else "DAY"
    mode_color = (100, 160, 220) if night else (220, 200, 120)
    dot_color = (80, 140, 200) if night else (200, 180, 80)
    draw.ellipse([6, 10, 12, 16], fill=dot_color)
    draw.text((16, 6), mode_text, mode_color, f_tiny)
    
    # 中间：日期 + 星期 + 农历（一行显示）
    month = now.month
    day = now.day
    weekdays = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    weekday = weekdays[now.weekday()]
    
    # 农历
    lunar_text = ""
    try:
        lunar = ZhDate.from_datetime(now)
        lunar_month_names = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
        lunar_day_names = ["初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
                          "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
                          "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"]
        lunar_text = f"{lunar_month_names[lunar.lunar_month - 1]}月{lunar_day_names[lunar.lunar_day - 1]}"
    except Exception:
        pass
    
    # 组合日期文本
    date_text = f"{month:02d}/{day:02d} {weekday}"
    if lunar_text:
        date_text += f" {lunar_text}"
    
    date_bbox = draw.textbbox((0, 0), date_text, f_sm)
    date_w = date_bbox[2] - date_bbox[0]
    date_x = (W - date_w) // 2
    
    is_weekend = now.weekday() >= 5
    date_color = (255, 180, 120) if is_weekend else (220, 225, 235)
    draw.text((date_x, 8), date_text, date_color, f_sm)
    
    # 右侧：生活指数
    if info.get('life'):
        life_text = get_clothing_advice(info['life'])
        life_bbox = draw.textbbox((0, 0), life_text, f_tiny)
        life_w = life_bbox[2] - life_bbox[0]
        life_x = W - life_w - 8
        draw.rounded_rectangle([life_x - 3, 5, life_x + life_w + 3, 19], 3, fill=(40, 35, 25))
        draw.text((life_x, 6), life_text, (255, 200, 100), f_tiny)
    
    # ========== 2. 加载辉光管素材图片 (带全局缓存) ==========
    global NIXIE_IMAGE_CACHE
    if 'NIXIE_IMAGE_CACHE' not in globals():
        NIXIE_IMAGE_CACHE = {}
    
    nixie_dir = os.path.join(BASE_DIR, "辉光管素材图")
    tube_target_h = 110
    width_scale = 1.45
    
    # 如果缓存为空，则加载一次
    if not NIXIE_IMAGE_CACHE:
        logger.info("正在加载辉光管素材至内存缓存...")
        for d in range(10):
            try:
                img_path = f"{nixie_dir}/{d}.png"
                if os.path.exists(img_path):
                    nixie_img = Image.open(img_path).convert("RGBA")
                    ratio = tube_target_h / nixie_img.height
                    new_w = int(nixie_img.width * ratio * width_scale)
                    nixie_img = nixie_img.resize((new_w, tube_target_h), Image.Resampling.LANCZOS)
                    NIXIE_IMAGE_CACHE[str(d)] = nixie_img
                else:
                    logger.warning(f"素材文件不存在: {img_path}")
            except Exception as e:
                logger.warning(f"加载辉光管素材 {d}.png 失败: {e}")
    
    nixie_images = NIXIE_IMAGE_CACHE
    
    # ========== 3. 计算布局 ==========
    time_str = now.strftime("%H%M")
    digits = list(time_str)
    
    # 获取单个管子宽度
    if nixie_images:
        sample_img = list(nixie_images.values())[0]
        tube_w = sample_img.width
        tube_h = sample_img.height
    else:
        tube_w, tube_h = 75, 110  # 备用尺寸
    
    colon_w = 10  # 冒号区域宽度
    gap = 2  # 管子间距
    total_w = tube_w * 4 + colon_w + gap * 3
    start_x = (W - total_w) // 2
    base_y = 28  # 图片顶部Y坐标
    
    # ========== 4. 绘制4个辉光管数字 ==========
    positions = []
    curr_x = start_x
    
    for i, digit in enumerate(digits):
        positions.append(curr_x)
        
        # 粘贴数字图片
        if digit in nixie_images:
            nixie_img = nixie_images[digit]
            img.paste(nixie_img, (curr_x, base_y), nixie_img)
        else:
            draw.text((curr_x + 15, base_y + 30), digit, (255, 140, 40), f_renix_big)
        
        curr_x += tube_w + gap
        
        # 在第2个管子后留出间距
        if i == 1:
            curr_x += colon_w
    
    # ========== 5. 底部天气卡片区域 ==========
    draw_forecast_cards(draw, 155, night)
    
    # ========== 8. 底部信息栏 ==========
    footer_y = H - 16
    
    # 底部背景
    draw.rectangle([0, footer_y, W, H], fill=(bg_top[0] + 5, bg_top[1] + 6, bg_top[2] + 8))
    draw.line([0, footer_y, W, footer_y], fill=(accent[0] + 20, accent[1] + 30, accent[2] + 40))
    
    text_y = footer_y + 3
    
    # 左侧：运行时间
    uptime = info.get('uptime', '0天0时')
    draw.text((6, text_y), uptime, (100, 160, 140), f_tiny)
    
    # 中间：BTC价格
    crypto_data = info.get('crypto', [])
    btc_price = 0
    for c in crypto_data:
        if c.get('name') == 'BTC':
            try:
                btc_price = float(c.get('price', 0))
            except:
                pass
            break
    if btc_price > 0:
        btc_str = f"BTC:{btc_price/1000:.1f}K"
        draw.text((W // 2 - 30, text_y), btc_str, (255, 200, 100), f_tiny)
    
    # 右侧：直播数或CPU温度
    streamers = info.get("bilibili_streamers", [])
    live_count = sum(1 for s in streamers if s.get("live_status") == 1)
    if live_count > 0:
        live_text = f"LIVE:{live_count}"
        draw.text((W - 50, text_y), live_text, (251, 114, 153), f_tiny)
    else:
        cpu_t = info.get('cpu_t', 0)
        temp_color = (255, 80, 80) if cpu_t > 70 else (255, 200, 100) if cpu_t > 55 else (100, 180, 150)
        draw.text((W - 42, text_y), f"{cpu_t}C", temp_color, f_tiny)
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img

def draw_mini_kline(draw: ImageDraw.Draw, x: int, y: int, w: int, h: int, 
                    data: List[float], up_color: tuple = (100, 255, 180), 
                    down_color: tuple = (255, 100, 100)) -> None:
    """绘制迷你K线图（蜡烛图样式）"""
    if not data or len(data) < 2:
        return
    
    n = len(data)
    bar_width = max(3, (w - n * 2) // n)
    gap = 1
    total_bar_width = bar_width + gap
    
    # 计算数据范围，扩展以容纳影线
    min_val = min(data)
    max_val = max(data)
    margin = (max_val - min_val) * 0.15 if max_val != min_val else max_val * 0.01
    min_val -= margin
    max_val += margin
    val_range = max_val - min_val if max_val != min_val else 1
    
    # 绘制每根K线蜡烛
    for i in range(1, n):
        prev_val = data[i - 1]
        curr_val = data[i]
        
        bx = x + (i - 1) * total_bar_width
        center_x = bx + bar_width // 2
        
        # 开盘价、收盘价
        open_price = prev_val
        close_price = curr_val
        
        # 模拟高低价（基于开收盘价波动）
        volatility = abs(curr_val - prev_val) * 0.15
        high_price = max(open_price, close_price) + volatility
        low_price = min(open_price, close_price) - volatility
        
        # 归一化到像素坐标
        high_y = y + int((1 - (high_price - min_val) / val_range) * h)
        low_y = y + int((1 - (low_price - min_val) / val_range) * h)
        open_y = y + int((1 - (open_price - min_val) / val_range) * h)
        close_y = y + int((1 - (close_price - min_val) / val_range) * h)
        
        # 限制Y坐标范围
        high_y = max(y, min(y + h, high_y))
        low_y = max(y, min(y + h, low_y))
        open_y = max(y, min(y + h, open_y))
        close_y = max(y, min(y + h, close_y))
        
        # 涨跌颜色
        is_up = close_price >= open_price
        color = up_color if is_up else down_color
        
        # 绘制影线（上下细线）
        draw.line([center_x, high_y, center_x, low_y], fill=color, width=1)
        
        # 绘制实体（蜡烛主体）
        body_top = min(open_y, close_y)
        body_bottom = max(open_y, close_y)
        if body_bottom - body_top < 1:
            body_bottom = body_top + 1
        draw.rectangle([bx, body_top, bx + bar_width, body_bottom], fill=color)


def draw_crypto() -> Image.Image:
    """绘制加密货币监控页面 - 资产+三币种K线图"""
    night = is_night_mode()
    
    # 使用动态背景
    img = create_dynamic_background()
    draw = ImageDraw.Draw(img)
    bg_top, _, accent = get_time_based_colors()
    
    # 颜色定义
    up_color = (38, 166, 91)
    down_color = (234, 57, 67)
    grid_color = (bg_top[0] + 15, bg_top[1] + 20, bg_top[2] + 25)
    text_dim = (100, 110, 130)
    text_bright = (200, 210, 225)
    
    # ===== 顶部资产栏 (高度24px) =====
    header_h = 24
    draw.rectangle([0, 0, W, header_h], fill=(bg_top[0] + 8, bg_top[1] + 10, bg_top[2] + 12))
    
    # 资产信息
    draw.text((4, 2), "ASSETS", text_dim, f_tiny)
    asset_str = info.get('bybit_asset', 'Loading...')
    draw.text((50, 2), asset_str, (255, 230, 100), f_tiny)
    
    # 资产变化
    asset_history = info.get("bybit_asset_history", [])
    if len(asset_history) >= 2:
        first_val = asset_history[0][1]
        last_val = asset_history[-1][1]
        if first_val > 0:
            asset_change = ((last_val - first_val) / first_val) * 100
            change_color = up_color if asset_change >= 0 else down_color
            draw.text((130, 2), f"{asset_change:+.1f}%", change_color, f_tiny)
    
    # 时间
    now = datetime.now()
    draw.text((W - 30, 2), now.strftime("%H:%M"), text_dim, f_tiny)
    
    # 资产迷你图
    if len(asset_history) >= 3:
        prices = [p[1] for p in asset_history[-15:]]
        draw_mini_kline(draw, 170, 4, 80, 16, prices, up_color, down_color)
    
    draw.line([0, header_h, W, header_h], fill=(40, 50, 65))
    
    # ===== 三个币种K线图区域 =====
    crypto_data = info.get("crypto", [])
    crypto_klines = info.get("crypto_klines", {})
    
    # 3列布局
    content_y = header_h + 2
    content_h = H - header_h - 4
    col_w = W // 3
    
    coin_names = ["BTC", "ETH", "DOGE"]
    
    for col_idx, coin_name in enumerate(coin_names):
        cx = col_idx * col_w
        
        # 找到对应币种数据
        coin_data = None
        for c in crypto_data:
            if c.get("name") == coin_name:
                coin_data = c
                break
        
        # 币种标题栏
        title_h = 28
        draw.rectangle([cx, content_y, cx + col_w - 1, content_y + title_h], fill=(20, 25, 32))
        
        if coin_data:
            price = coin_data.get("price", "0")
            change = coin_data.get("change", 0)
            is_up = change >= 0
            color = up_color if is_up else down_color
            
            # 币种名
            draw.text((cx + 3, content_y + 2), coin_name, text_bright, f_tiny)
            
            # 价格
            price_str = f"${price}" if float(price) >= 1 else f"${float(price):.4f}"
            if len(price_str) > 10:
                price_str = f"${float(price):.0f}"
            draw.text((cx + 3, content_y + 14), price_str, color, f_tiny)
            
            # 涨跌幅
            change_str = f"{change:+.1f}%"
            draw.text((cx + col_w - 36, content_y + 8), change_str, color, f_tiny)
        else:
            draw.text((cx + 3, content_y + 8), coin_name, text_dim, f_tiny)
        
        # K线图区域
        chart_x = cx + 2
        chart_y = content_y + title_h + 2
        chart_w = col_w - 4
        chart_h = content_h - title_h - 8
        
        # 网格线
        for i in range(4):
            gy = chart_y + i * (chart_h // 3)
            draw.line([chart_x, gy, chart_x + chart_w, gy], fill=grid_color)
        
        # 使用真实K线数据绘制蜡烛图
        klines = crypto_klines.get(coin_name, [])
        if len(klines) >= 3:
            # 提取OHLC数据
            all_highs = [k["high"] for k in klines]
            all_lows = [k["low"] for k in klines]
            
            min_p = min(all_lows)
            max_p = max(all_highs)
            # 扩展范围
            margin = (max_p - min_p) * 0.05 if max_p != min_p else max_p * 0.01
            min_p -= margin
            max_p += margin
            p_range = max_p - min_p if max_p != min_p else 1
            
            n = len(klines)
            kline_w = chart_w - 6
            bar_w = max(3, (kline_w - n) // n)
            gap = 1
            
            for i, kline in enumerate(klines):
                open_p = kline["open"]
                high_p = kline["high"]
                low_p = kline["low"]
                close_p = kline["close"]
                
                bx = chart_x + i * (bar_w + gap)
                center_x = bx + bar_w // 2
                
                # 计算Y坐标
                high_y = chart_y + int((1 - (high_p - min_p) / p_range) * chart_h)
                low_y = chart_y + int((1 - (low_p - min_p) / p_range) * chart_h)
                open_y = chart_y + int((1 - (open_p - min_p) / p_range) * chart_h)
                close_y = chart_y + int((1 - (close_p - min_p) / p_range) * chart_h)
                
                # 限制Y坐标范围
                high_y = max(chart_y, min(chart_y + chart_h, high_y))
                low_y = max(chart_y, min(chart_y + chart_h, low_y))
                open_y = max(chart_y, min(chart_y + chart_h, open_y))
                close_y = max(chart_y, min(chart_y + chart_h, close_y))
                
                is_up = close_p >= open_p
                color = up_color if is_up else down_color
                
                # 影线
                draw.line([center_x, high_y, center_x, low_y], fill=color, width=1)
                
                # 实体
                body_top = min(open_y, close_y)
                body_bottom = max(open_y, close_y)
                if body_bottom - body_top < 2:
                    body_bottom = body_top + 2
                draw.rectangle([bx, body_top, bx + bar_w, body_bottom], fill=color)
            
            # 右侧当前价格标签
            if coin_data:
                curr_price = float(coin_data.get("price", 0))
                change = coin_data.get("change", 0)
                is_up = change >= 0
                price_color = up_color if is_up else down_color
                
                # 计算当前价格的Y位置
                price_y = chart_y + int((1 - (curr_price - min_p) / p_range) * chart_h)
                price_y = max(chart_y + 4, min(chart_y + chart_h - 10, price_y))
                
                # 价格横线（虚线效果）
                for lx in range(chart_x, cx + col_w - 2, 4):
                    draw.line([lx, price_y, lx + 2, price_y], fill=price_color)
                
                # 右边缘价格标记
                label_x = cx + col_w - 2
                draw.rectangle([label_x - 1, price_y - 5, label_x + 1, price_y + 5], fill=price_color)
        else:
            draw.text((cx + col_w // 2 - 10, chart_y + chart_h // 2), "...", text_dim, f_tiny)
        
        # 列分隔线
        if col_idx < 2:
            draw.line([cx + col_w - 1, content_y, cx + col_w - 1, H], fill=grid_color)
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img

def draw_calendar() -> Image.Image:
    """绘制日历页面 - 美化版"""
    night = is_night_mode()
    now = datetime.now()
    
    # 使用动态背景
    img = create_dynamic_background()
    draw = ImageDraw.Draw(img)
    bg_top, _, accent = get_time_based_colors()
    
    # ===== 顶部标题区域 =====
    # 月份（大字）
    month_names = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", 
                   "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
    month_str = month_names[now.month - 1]
    year_str = str(now.year)
    
    # 月份用大号字体
    draw.text((15, 4), month_str, (100, 180, 255), f_mid)
    # 年份用小号字体
    month_bbox = draw.textbbox((0, 0), month_str, f_mid)
    month_width = month_bbox[2] - month_bbox[0]
    draw.text((20 + month_width, 10), year_str, (120, 130, 150), f_sm)
    
    # 右侧显示农历
    try:
        lunar = ZhDate.from_datetime(now)
        lunar_month_names = ["正", "二", "三", "四", "五", "六", "七", "八", "九", "十", "冬", "腊"]
        lunar_day_names = ["初一", "初二", "初三", "初四", "初五", "初六", "初七", "初八", "初九", "初十",
                          "十一", "十二", "十三", "十四", "十五", "十六", "十七", "十八", "十九", "二十",
                          "廿一", "廿二", "廿三", "廿四", "廿五", "廿六", "廿七", "廿八", "廿九", "三十"]
        lunar_str = f"{lunar_month_names[lunar.lunar_month - 1]}月{lunar_day_names[lunar.lunar_day - 1]}"
        lunar_bbox = draw.textbbox((0, 0), lunar_str, f_sm)
        lunar_width = lunar_bbox[2] - lunar_bbox[0]
        draw.text((W - lunar_width - 12, 8), lunar_str, (200, 160, 100), f_sm)
    except:
        pass
    
    # 分隔线
    draw.rectangle([15, 28, W - 15, 29], fill=(50, 60, 80))
    
    # ===== 日历网格 =====
    cal = calendar.monthcalendar(now.year, now.month)
    days_header = ["一", "二", "三", "四", "五", "六", "日"]
    
    # 布局参数
    start_x = 8
    start_y = 36
    cell_w = 44
    cell_h = 24
    
    # 绘制星期头
    for i, d in enumerate(days_header):
        x = start_x + i * cell_w + cell_w // 2
        # 周末用不同颜色
        if i >= 5:  # 周六、周日
            color = (255, 140, 100)
        else:
            color = (100, 120, 150)
        # 居中绘制
        d_bbox = draw.textbbox((0, 0), d, f_tiny)
        d_width = d_bbox[2] - d_bbox[0]
        draw.text((x - d_width // 2, start_y), d, color, f_tiny)
    
    # 星期头下方的细线
    draw.rectangle([start_x, start_y + 14, start_x + 7 * cell_w - 4, start_y + 15], fill=(40, 50, 65))
    
    # 绘制日期
    curr_y = start_y + 20
    for week in cal:
        for i, day in enumerate(week):
            if day != 0:
                x = start_x + i * cell_w + cell_w // 2
                is_today = (day == now.day)
                is_weekend = (i >= 5)
                
                # 日期文本
                day_str = str(day)
                day_bbox = draw.textbbox((0, 0), day_str, f_sm)
                day_width = day_bbox[2] - day_bbox[0]
                day_height = day_bbox[3] - day_bbox[1]
                
                if is_today:
                    # 今天：圆形高亮背景
                    cx = x
                    cy = curr_y + day_height // 2 + 1
                    radius = 11
                    
                    # 外发光
                    for r in range(radius + 4, radius, -1):
                        alpha = (radius + 4 - r) / 4
                        glow = (int(60 * alpha), int(140 * alpha), int(255 * alpha))
                        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=glow)
                    
                    # 主圆形
                    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], 
                                fill=(50, 130, 255))
                    # 文字
                    draw.text((x - day_width // 2, curr_y), day_str, (255, 255, 255), f_sm)
                else:
                    # 普通日期
                    if is_weekend:
                        color = (220, 130, 100)  # 周末橙红色
                    else:
                        color = (180, 190, 210)  # 工作日浅色
                    draw.text((x - day_width // 2, curr_y), day_str, color, f_sm)
        
        curr_y += cell_h
    
    # ===== 底部倒计时区域 =====
    countdown_y = 178
    
    # 分隔装饰线
    draw.rectangle([20, countdown_y - 8, W - 20, countdown_y - 7], fill=(45, 55, 70))
    # 两端装饰点
    draw.ellipse([18, countdown_y - 10, 24, countdown_y - 4], fill=(80, 140, 200))
    draw.ellipse([W - 24, countdown_y - 10, W - 18, countdown_y - 4], fill=(80, 140, 200))
    
    # 倒计时计算
    days_left = (TARGET_DATE - now).days
    
    # 左侧标签
    draw.text((20, countdown_y), "COUNTDOWN", (100, 110, 130), f_tiny)
    draw.text((20, countdown_y + 12), TARGET_NAME, (140, 150, 170), f_tiny)
    
    # 右侧天数（大号醒目）
    if days_left > 0:
        days_str = str(days_left)
        # 天数
        days_bbox = draw.textbbox((0, 0), days_str, f_big)
        days_width = days_bbox[2] - days_bbox[0]
        days_x = W - days_width - 55
        
        # 数字颜色（根据剩余天数变化）
        if days_left <= 7:
            num_color = (255, 80, 80)  # 红色紧急
        elif days_left <= 30:
            num_color = (255, 180, 80)  # 橙色
        else:
            num_color = (100, 200, 255)  # 蓝色
        
        draw.text((days_x, countdown_y - 2), days_str, num_color, f_big)
        
        # "DAYS" 标签
        draw.text((W - 50, countdown_y + 8), "DAYS", (120, 130, 150), f_tiny)
    else:
        draw.text((W - 80, countdown_y + 5), "已到期", (255, 100, 100), f_sm)
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img


def format_speed(bytes_per_sec: float) -> str:
    """格式化速度 (B/s -> KB/s, MB/s)"""
    if bytes_per_sec < 1024:
        return f"{bytes_per_sec:.0f}B/s"
    elif bytes_per_sec < 1024 * 1024:
        return f"{bytes_per_sec / 1024:.1f}K"
    else:
        return f"{bytes_per_sec / (1024 * 1024):.1f}M"


def draw_mini_bar(draw, x: int, y: int, width: int, height: int, value: float, 
                   bar_color: tuple, bg_color: tuple = (40, 45, 55)) -> None:
    """绘制迷你进度条"""
    # 背景
    draw.rounded_rectangle([x, y, x + width, y + height], 2, fill=bg_color)
    # 进度
    fill_width = max(2, int(width * min(value, 100) / 100))
    if fill_width > 2:
        draw.rounded_rectangle([x, y, x + fill_width, y + height], 2, fill=bar_color)


def draw_beszel() -> Image.Image:
    """绘制Beszel服务器监控页面 - 美化版"""
    night = is_night_mode()
    
    # 使用动态背景
    img = create_dynamic_background()
    draw = ImageDraw.Draw(img)
    bg_top, _, accent = get_time_based_colors()
    
    # 顶部标题栏（渐变 + 底部发光线）
    header_h = 30
    for y in range(header_h):
        alpha = y / header_h
        r = int((bg_top[0] + 12) * (1 - alpha) + bg_top[0] * alpha)
        g = int((bg_top[1] + 15) * (1 - alpha) + bg_top[1] * alpha)
        b = int((bg_top[2] + 20) * (1 - alpha) + bg_top[2] * alpha)
        draw.rectangle([0, y, W, y + 1], fill=(r, g, b))
    
    # 底部发光线
    draw.rectangle([0, header_h - 1, W, header_h], fill=(60, 140, 200))
    draw.rectangle([0, header_h, W, header_h + 1], fill=(30, 70, 100))
    
    # 标题图标 + 文字
    draw.text((8, 5), "[S]", (80, 180, 255), f_sm)
    draw.text((28, 6), "SERVER MONITOR", (220, 230, 245), f_sm)
    
    # 在线统计（标题栏中间）
    clients = info.get("beszel_clients", [])
    total_clients = len(clients)
    online_count = sum(1 for c in clients if "on" in str(c.get("status", "")).lower() or c.get("status") == "up")
    status_text = f"{online_count}/{total_clients}"
    status_color = (80, 200, 120) if online_count == total_clients else (255, 180, 80)
    draw.text((W // 2 - 10, 8), status_text, status_color, f_tiny)
    
    # 当前时间（右侧）
    now = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    time_bbox = draw.textbbox((0, 0), time_str, f_tiny)
    time_width = time_bbox[2] - time_bbox[0]
    draw.text((W - time_width - 8, 9), time_str, (120, 160, 200), f_tiny)
    
    if not clients:
        status = info.get("beszel_status", "Loading...")
        # 加载动画效果
        draw.text((W // 2 - 40, 100), "⟳", (80, 140, 200), f_mid)
        draw_centered_text(draw, status, f_sm, 130, (100, 120, 150))
        return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
    
    # 网格配置 (2列 x 3行)
    cols = 2
    rows = 3
    margin_x, margin_y = 5, 34
    gap_x, gap_y = 5, 4
    block_w = (W - 2 * margin_x - (cols - 1) * gap_x) // cols
    block_h = (H - margin_y - 6 - (rows - 1) * gap_y) // rows
    
    for idx, client in enumerate(clients[:cols * rows]):
        col_idx = idx % cols
        row_idx = idx // cols
        bx = margin_x + col_idx * (block_w + gap_x)
        by = margin_y + row_idx * (block_h + gap_y)
        
        # 状态检测
        status_val = client.get("status", "unknown")
        is_online = "on" in str(status_val).lower() or status_val == "up"
        
        # 卡片背景（渐变效果）
        card_top = (28, 34, 45) if night else (35, 42, 55)
        card_bottom = (22, 26, 35) if night else (28, 32, 42)
        
        # 绘制渐变背景
        for cy in range(block_h):
            alpha = cy / block_h
            r = int(card_top[0] * (1 - alpha) + card_bottom[0] * alpha)
            g = int(card_top[1] * (1 - alpha) + card_bottom[1] * alpha)
            b = int(card_top[2] * (1 - alpha) + card_bottom[2] * alpha)
            draw.rectangle([bx + 1, by + cy, bx + block_w - 1, by + cy + 1], fill=(r, g, b))
        
        # 卡片边框
        border_color = (60, 180, 120) if is_online else (180, 80, 80)
        draw.rounded_rectangle(
            [bx, by, bx + block_w, by + block_h],
            5, fill=None, outline=(50, 58, 72), width=1
        )
        
        # 顶部状态条（细线）
        draw.rectangle([bx + 4, by + 1, bx + block_w - 4, by + 2], fill=border_color)
        
        # 设备名称 + 状态点
        name = client.get("name", "Unknown")[:10]
        # 状态圆点
        dot_x = bx + 7
        dot_y = by + 10
        dot_r = 3
        draw.ellipse([dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r], 
                     fill=border_color)
        # 发光效果
        glow_color = (border_color[0] // 3, border_color[1] // 3, border_color[2] // 3)
        draw.ellipse([dot_x - dot_r - 2, dot_y - dot_r - 2, dot_x + dot_r + 2, dot_y + dot_r + 2], 
                     fill=None, outline=glow_color, width=1)
        
        # 设备名称 + 温度（右侧）
        name = client.get("name", "Unknown")[:10]
        draw.text((bx + 14, by + 4), name, (235, 240, 250), f_sm)
        
        # 温度显示在名称右侧
        temp = client.get("temperature", 0)
        if temp > 0:
            temp_color = (255, 120, 120) if temp > 70 else (255, 200, 120) if temp > 55 else (120, 200, 160)
            draw.text((bx + block_w - 38, by + 5), f"{temp:.0f}C", temp_color, f_tiny)
        
        # ===== 指标显示区域（4行紧凑布局）=====
        row_h = 12  # 每行高度
        metrics_y = by + 18
        bar_width = 48
        bar_height = 5
        label_x = bx + 5
        bar_x = bx + 26
        value_x = bx + 78
        
        # 第1行: CPU
        cpu = client.get("cpu", 0)
        cpu_color = (255, 100, 100) if cpu > 80 else (255, 200, 100) if cpu > 50 else (100, 200, 255)
        draw.text((label_x, metrics_y), "CPU", (130, 140, 160), f_tiny)
        draw_mini_bar(draw, bar_x, metrics_y + 3, bar_width, bar_height, cpu, cpu_color)
        draw.text((value_x, metrics_y), f"{cpu:>5.1f}%", cpu_color, f_tiny)
        
        # 第2行: RAM
        metrics_y += row_h
        ram = client.get("memory", 0)
        ram_color = (255, 100, 100) if ram > 85 else (255, 200, 100) if ram > 60 else (100, 255, 180)
        draw.text((label_x, metrics_y), "RAM", (130, 140, 160), f_tiny)
        draw_mini_bar(draw, bar_x, metrics_y + 3, bar_width, bar_height, ram, ram_color)
        draw.text((value_x, metrics_y), f"{ram:>5.1f}%", ram_color, f_tiny)
        
        # 第3行: DSK
        metrics_y += row_h
        disk = client.get("disk", 0)
        disk_color = (255, 100, 100) if disk > 90 else (255, 200, 100) if disk > 70 else (150, 200, 255)
        draw.text((label_x, metrics_y), "DSK", (130, 140, 160), f_tiny)
        draw_mini_bar(draw, bar_x, metrics_y + 3, bar_width, bar_height, disk, disk_color)
        draw.text((value_x, metrics_y), f"{disk:>5.1f}%", disk_color, f_tiny)
        
        # 第4行: LOAD（负载）
        metrics_y += row_h
        load = client.get("load", [0, 0, 0])
        ld_val = load[0] if isinstance(load, list) and load else 0
        ld_color = (255, 120, 120) if ld_val > 2 else (255, 200, 120) if ld_val > 1 else (150, 180, 220)
        draw.text((label_x, metrics_y), "LD", (130, 140, 160), f_tiny)
        # 负载用数字显示（不用进度条）
        draw.text((bar_x, metrics_y), f"{ld_val:.2f}", ld_color, f_tiny)
    
    # 底部更新时间
    last_update = info.get("beszel_last_update", 0)
    if last_update > 0:
        update_ago = int(time.time() - last_update)
        if update_ago < 60:
            update_text = f"Updated {update_ago}s ago"
        else:
            update_text = f"Updated {update_ago // 60}m ago"
        draw.text((W - 80, H - 14), update_text, (100, 110, 130), f_tiny)
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img


def draw_telegram() -> Image.Image:
    """绘制Telegram频道消息页面 - 多频道独立显示"""
    night = is_night_mode()
    
    # 使用动态背景
    img = create_dynamic_background()
    draw = ImageDraw.Draw(img)
    bg_top, _, accent = get_time_based_colors()
    
    # ===== 顶部标题栏 =====
    header_h = 18
    header_color = (bg_top[0] + 14, bg_top[1] + 18, bg_top[2] + 22)
    draw.rectangle([0, 0, W, header_h], fill=header_color)
    
    draw.text((6, 2), "Telegram", (100, 180, 255), f_sm)
    
    # 状态指示
    status = info.get("telegram_status", "Loading...")
    status_color = (100, 200, 150) if status == "Updated" else (200, 150, 100)
    draw.ellipse([W - 14, 5, W - 8, 11], fill=status_color)
    
    # 频道数量
    channels = info.get("telegram_channels", [])
    if channels:
        draw.text((W - 50, 3), f"{len(channels)}ch", (100, 120, 150), f_tiny)
    
    draw.line([0, header_h, W, header_h], fill=(50, 65, 80))
    
    # ===== 频道消息区域 =====
    channel_data = info.get("telegram_channel_data", [])
    thumbs = info.get("telegram_thumbs", {})
    
    if not channel_data:
        draw.text((W // 2 - 40, H // 2 - 10), "Loading...", (120, 130, 150), f_sm)
        draw.text((W // 2 - 55, H // 2 + 10), "等待消息加载", (100, 110, 130), f_tiny)
        return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
    
    # 计算每个频道的高度
    content_h = H - header_h - 4
    num_channels = len(channel_data)
    channel_h = content_h // max(num_channels, 1)
    
    for ch_idx, ch_data in enumerate(channel_data):
        ch_y = header_h + 2 + ch_idx * channel_h
        ch_title = ch_data.get("title", ch_data.get("username", ""))
        ch_username = ch_data.get("username", "")
        messages = ch_data.get("messages", [])
        
        # 频道标题栏
        title_h = 14
        draw.rectangle([2, ch_y, W - 2, ch_y + title_h], fill=(28, 38, 48))
        
        # 频道名（截取）
        if len(ch_title) > 20:
            ch_title = ch_title[:18] + ".."
        draw.text((6, ch_y + 1), ch_title, (80, 160, 230), f_tiny)
        
        # @username
        draw.text((W - 70, ch_y + 1), f"@{ch_username[:8]}", (80, 100, 130), f_tiny)
        
        # 消息内容区域
        msg_y = ch_y + title_h + 2
        msg_h = channel_h - title_h - 6
        
        if not messages:
            draw.text((10, msg_y + msg_h // 2 - 5), "无消息", (100, 110, 130), f_tiny)
            continue
        
        msg = messages[0]  # 只显示最新一条
        
        # 检查是否有缩略图
        thumb_key = msg.get("thumb_key")
        has_thumb = thumb_key and thumb_key in thumbs
        
        # 左侧蓝色边条
        draw.rectangle([4, msg_y, 6, msg_y + msg_h - 2], fill=(80, 160, 230))
        
        content_x = 10
        thumb_w = 0
        
        # 显示缩略图
        if has_thumb:
            thumb_img = thumbs.get(thumb_key)
            if thumb_img:
                # 根据可用高度调整缩略图大小
                thumb_h = min(msg_h - 4, 55)
                thumb_w_calc = int(thumb_h * 1.3)
                try:
                    resized_thumb = thumb_img.resize((thumb_w_calc, thumb_h), Image.Resampling.LANCZOS)
                    img.paste(resized_thumb, (content_x, msg_y))
                    thumb_w = thumb_w_calc + 4
                    
                    # 视频播放图标
                    if msg.get("media_type") == "video":
                        play_x = content_x + thumb_w_calc // 2 - 7
                        play_y = msg_y + thumb_h // 2 - 8
                        draw.polygon([(play_x, play_y), (play_x, play_y + 12), (play_x + 10, play_y + 6)], 
                                   fill=(255, 255, 255))
                except:
                    thumb_w = 0
        
        # 消息文本
        text = msg.get("text", "")
        if not text:
            media_type = msg.get("media_type", "")
            if media_type == "photo":
                text = "[图片]"
            elif media_type == "video":
                text = "[视频]"
            elif media_type == "file":
                text = "[文件]"
            else:
                text = "[消息]"
        
        # 文本区域
        text_x = content_x + thumb_w
        text_w = W - text_x - 8
        max_chars = max(10, text_w // 6)
        
        # 分行
        lines = []
        current_line = ""
        for char in text:
            if char == '\n':
                if current_line:
                    lines.append(current_line)
                current_line = ""
            else:
                char_w = 2 if ord(char) > 127 else 1
                line_w = sum(2 if ord(c) > 127 else 1 for c in current_line)
                if line_w + char_w > max_chars:
                    lines.append(current_line)
                    current_line = char
                else:
                    current_line += char
        if current_line:
            lines.append(current_line)
        
        # 显示文本
        max_lines = max(1, (msg_h - 14) // 11)
        for line_idx, line in enumerate(lines[:max_lines]):
            if line_idx == max_lines - 1 and len(lines) > max_lines:
                line = line[:max_chars - 2] + ".."
            draw.text((text_x, msg_y + line_idx * 11), line, (210, 215, 225), f_tiny)
        
        # 底部信息：浏览量 + 时间
        info_y = msg_y + msg_h - 12
        views = msg.get("views", 0)
        if views > 0:
            views_str = f"{views/1000:.1f}K" if views >= 1000 else str(views)
            draw.text((text_x, info_y), f"V:{views_str}", (90, 120, 160), f_tiny)
        
        date_str = msg.get("date", "")
        if date_str:
            draw.text((W - 62, info_y), date_str, (100, 110, 130), f_tiny)
        
        # 频道分隔线
        if ch_idx < num_channels - 1:
            sep_y = ch_y + channel_h - 1
            draw.line([4, sep_y, W - 4, sep_y], fill=(40, 50, 65))
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img


def draw_tracking() -> Image.Image:
    """绘制物流追踪页面 - 美化版"""
    night = is_night_mode()
    
    # 使用动态背景
    img = create_dynamic_background()
    draw = ImageDraw.Draw(img)
    bg_top, _, accent = get_time_based_colors()
    
    # 顶部标题栏
    header_h = 24
    draw.rectangle([0, 0, W, header_h], fill=(bg_top[0] + 10, bg_top[1] + 12, bg_top[2] + 18))
    draw.rectangle([0, header_h - 2, W, header_h], fill=(80, 180, 120))
    
    # 标题
    draw.text((6, 4), "PACKAGE", (80, 200, 140), f_sm)
    
    # 包裹数量 + 时间
    packages = info.get("tracking_packages", [])
    now = datetime.now()
    draw.text((W // 2 - 8, 6), f"{len(packages)}件", (150, 200, 160), f_tiny)
    draw.text((W - 38, 6), now.strftime("%H:%M"), (120, 160, 200), f_tiny)
    
    if not packages:
        draw_centered_text(draw, "暂无包裹", f_sm, 100, (100, 120, 150))
        draw_centered_text(draw, "访问 :8080 添加", f_tiny, 125, (80, 100, 130))
        return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
    
    # 内容区域
    content_y = header_h + 4
    content_h = H - content_y - 4
    pkg_count = len(packages)
    
    # 单包裹全屏，多包裹上下分割
    if pkg_count == 1:
        card_h = content_h
    else:
        card_h = (content_h - 4) // min(pkg_count, 2)
    
    for idx, pkg in enumerate(packages[:2]):  # 最多显示2个包裹
        cy = content_y + idx * (card_h + 4)
        
        # 卡片背景
        draw.rounded_rectangle([4, cy, W - 4, cy + card_h], 6, fill=(bg_top[0] + 8, bg_top[1] + 10, bg_top[2] + 14))
        
        # 获取包裹信息
        alias = pkg.get("alias", "") or pkg.get("carrier_name", "包裹")
        carrier = pkg.get("carrier_name", "")
        tracks = pkg.get("tracks", [])
        tn = pkg.get("tracking_number", "")
        
        # 第一行：包裹名称 + 快递公司
        # 计算可用宽度（中文约10px，英文约6px）
        def text_width(s):
            return sum(10 if ord(c) > 127 else 6 for c in s)
        
        max_alias_w = 120
        alias_display = alias
        while text_width(alias_display) > max_alias_w and len(alias_display) > 1:
            alias_display = alias_display[:-1]
        if alias_display != alias:
            alias_display += ".."
        
        draw.text((10, cy + 4), alias_display, (255, 255, 255), f_sm)
        
        # 右侧：快递公司 + 单号后6位
        carrier_short = carrier[:4] if carrier else ""
        tn_short = tn[-6:] if len(tn) > 6 else tn
        right_text = f"{carrier_short} {tn_short}"
        right_w = text_width(right_text)
        draw.text((W - right_w - 10, cy + 5), right_text, (100, 120, 150), f_tiny)
        
        # 分隔线
        draw.line([10, cy + 22, W - 10, cy + 22], fill=(50, 60, 80))
        
        # 物流信息
        track_y = cy + 26
        available_track_h = card_h - 30
        
        if not tracks:
            draw.text((10, track_y + 4), "等待揽收中...", (120, 130, 150), f_tiny)
        else:
            # 显示最新的物流信息（根据卡片高度决定显示几条）
            max_tracks = 1 if available_track_h < 40 else 2
            line_h = min(36, available_track_h // max_tracks)
            
            for i, track in enumerate(tracks[:max_tracks]):
                ty = track_y + i * line_h
                
                # 时间
                track_time = track.get("time", "")
                if track_time:
                    try:
                        dt = datetime.strptime(track_time, "%Y-%m-%d %H:%M:%S")
                        time_short = dt.strftime("%m-%d %H:%M")
                    except:
                        time_short = track_time[-11:] if len(track_time) > 11 else track_time
                    draw.text((10, ty), time_short, (80, 150, 200), f_tiny)
                
                # 物流内容 - 严格截断
                context = track.get("context", "")
                # 清理广告内容
                for noise in ["物流问题", "请致电", "如有疑问", "客服电话"]:
                    if noise in context:
                        context = context.split(noise)[0].strip()
                
                # 计算最大字符数（屏幕宽度320，左右边距各10，每个中文约10px）
                max_w = W - 24  # 可用宽度
                context_display = ""
                current_w = 0
                for c in context:
                    char_w = 10 if ord(c) > 127 else 6
                    if current_w + char_w > max_w:
                        context_display += ".."
                        break
                    context_display += c
                    current_w += char_w
                
                draw.text((10, ty + 13), context_display, (180, 190, 210), f_tiny)
        
        # 左侧状态指示条
        has_tracks = len(tracks) > 0
        status_color = (80, 200, 140) if has_tracks else (200, 150, 80)
        draw.rounded_rectangle([4, cy, 7, cy + card_h], 3, fill=status_color)
    
    # 如果有更多包裹
    if pkg_count > 2:
        draw.text((W - 55, H - 14), f"+{pkg_count - 2} 更多", (100, 120, 150), f_tiny)
    
    return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img


def draw_bilibili() -> Image.Image:
    """绘制B站主播监控大看板"""
    try:
        night = is_night_mode()
        
        # 使用动态背景
        img = create_dynamic_background()
        draw = ImageDraw.Draw(img)
        
        # ========== 顶部状态栏 (高度14px) ==========
        header_h = 14
        bg_top, _, accent = get_time_based_colors()
        draw.rectangle([0, 0, W, header_h], fill=(bg_top[0] + 12, bg_top[1] + 13, bg_top[2] + 17))
        draw.rectangle([0, header_h - 1, W, header_h], fill=(251, 114, 153))
        
        user = info.get("bilibili_user", {})
        now = datetime.now()
        streamers = info.get("bilibili_streamers", [])
        
        # 左侧: 用户信息
        x_pos = 4
        if user:
            uname = user.get("uname", "")[:5]
            level = user.get("level", 0)
            draw.text((x_pos, 1), uname, (255, 255, 255), f_tiny)
            uname_w = sum(10 if ord(c) > 127 else 6 for c in uname)
            x_pos += uname_w + 8
            lv_color = (251, 114, 153) if level >= 6 else (80, 140, 200)
            draw.text((x_pos, 1), f"Lv{level}", lv_color, f_tiny)
        
        # 右侧: 直播数/总数 + 时间
        live_count = sum(1 for s in streamers if s.get("live_status") == 1)
        total_count = len(streamers)
        status_text = f"{live_count}/{total_count}"
        draw.text((W - 70, 1), status_text, (251, 114, 153) if live_count > 0 else (100, 105, 120), f_tiny)
        draw.text((W - 30, 1), now.strftime("%H:%M"), (140, 145, 160), f_tiny)
        
        # ========== 主播卡片区域 ==========
        content_y = header_h + 2
        content_h = H - header_h - 4
        
        if not streamers:
            draw.text((W // 2 - 40, H // 2 - 10), "暂无关注主播", (100, 105, 120), f_sm)
            draw.text((W // 2 - 50, H // 2 + 10), "请在Web端添加主播", (80, 85, 100), f_tiny)
            return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
        
        # 按直播状态排序（直播中的排前面）
        sorted_streamers = sorted(streamers, key=lambda x: (x.get("live_status", 0) != 1, -x.get("online", 0)))
        
        # 计算布局: 2列显示，每列最多显示4个主播
        col_w = W // 2
        card_h = content_h // 4  # 每列4个卡片
        max_show = 8
        
        for idx, s in enumerate(sorted_streamers[:max_show]):
            col = idx % 2
            row = idx // 2
            
            cx = col * col_w + 2
            cy = content_y + row * card_h
            card_w = col_w - 4
            
            is_live = s.get("live_status") == 1
            alias = s.get("alias", "") or s.get("uname", "") or "主播"
            title = s.get("title", "")
            online = s.get("online", 0)
            area = s.get("area_name", "") or s.get("parent_area_name", "")
            
            # 卡片背景
            if is_live:
                bg_color = (35, 25, 30)  # 直播中 - 粉色调背景
                draw.rectangle([cx, cy, cx + card_w, cy + card_h - 2], fill=bg_color)
                # 左侧直播指示条
                draw.rectangle([cx, cy, cx + 2, cy + card_h - 2], fill=(251, 114, 153))
            else:
                bg_color = (28, 30, 38)  # 未直播 - 灰色背景
                draw.rectangle([cx, cy, cx + card_w, cy + card_h - 2], fill=bg_color)
                draw.rectangle([cx, cy, cx + 2, cy + card_h - 2], fill=(50, 55, 70))
            
            # 第一行: 主播名 + 状态
            name_display = alias[:6]
            name_color = (255, 255, 255) if is_live else (140, 145, 160)
            draw.text((cx + 5, cy + 2), name_display, name_color, f_tiny)
            
            if is_live:
                # 直播中标识
                draw.text((cx + card_w - 28, cy + 2), "LIVE", (251, 114, 153), f_tiny)
            
            # 第二行: 分区 + 人气
            if is_live:
                area_display = area[:4] if area else ""
                draw.text((cx + 5, cy + 14), area_display, (100, 180, 255), f_tiny)
                
                # 人气数
                if online > 0:
                    if online >= 10000:
                        online_str = f"{online/10000:.1f}w"
                    else:
                        online_str = str(online)
                    draw.text((cx + card_w - 30, cy + 14), online_str, (255, 180, 100), f_tiny)
            else:
                draw.text((cx + 5, cy + 14), "未开播", (80, 85, 100), f_tiny)
            
            # 第三行: 直播标题（仅直播中显示）
            if is_live and title:
                title_display = title[:12]
                if len(title) > 12:
                    title_display = title_display[:11] + ".."
                draw.text((cx + 5, cy + 26), title_display, (160, 165, 180), f_tiny)
        
        # 如果主播数超过8个，显示提示
        if len(streamers) > max_show:
            draw.text((W - 40, H - 12), f"+{len(streamers) - max_show}更多", (100, 105, 120), f_tiny)
        
        return adjust_brightness(img, NIGHT_DARKNESS_FACTOR) if night else img
        
    except Exception as e:
        logger.error(f"绘制B站页面失败: {e}")
        img = Image.new("RGB", (W, H), (18, 20, 28))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "B站页面错误", (200, 100, 100), f_sm)
        draw.text((10, 35), str(e)[:40], (150, 80, 80), f_tiny)
        return img


def main() -> None:
    """主函数"""
    import sys
    logger.info("启动智能屏幕显示系统")
    sys.stdout.flush()
    
    # 初始化显示器
    if not init_display():
        logger.error("显示器初始化失败，退出")
        return
    
    # 启动配置热加载
    config_reloader.start()
    
    logger.info("准备启动工作线程...")
    sys.stdout.flush()
    
    try:
        # 启动所有后台工作线程
    # 使用新的 SystemWorker 模块
        system_worker_instance = SystemWorker(info, SYSTEM_UPDATE_INTERVAL, logger)
        system_worker_instance.start()
    
        workers = [
            threading.Thread(target=weather_worker, daemon=True, name="WeatherWorker"),
            # threading.Thread(target=system_worker, daemon=True, name="SystemWorker"),  # 已迁移到模块
            threading.Thread(target=crypto_worker, daemon=True, name="CryptoWorker"),
            threading.Thread(target=tracking_worker, daemon=True, name="TrackingWorker"),
            threading.Thread(target=bilibili_worker, daemon=True, name="BilibiliWorker"),
            threading.Thread(target=tracking_web_worker, daemon=True, name="WebWorker"),
            threading.Thread(target=beszel_worker, daemon=True, name="BeszelWorker"),
            threading.Thread(target=telegram_worker, daemon=True, name="TelegramWorker"),
            threading.Thread(target=control_worker, daemon=True, name="ControlWorker"),
            threading.Thread(target=button_monitor_strict, daemon=True, name="ButtonMonitor")
        ]
        
        logger.info(f"创建了 {len(workers)} 个工作线程")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"创建线程失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    logger.info("按钮监控已启用（PC6引脚），同时支持UDP控制")
    logger.info(f"综合管理Web界面: http://0.0.0.0:{TRACKING_WEB_PORT}")
    
    for worker in workers:
        worker.start()
        logger.info(f"启动工作线程: {worker.name}")
    
    logger.info("所有线程已启动，开始主循环")
    
    # 主显示循环
    # 页面顺序: 时钟 -> 物流追踪 -> B站 -> 加密货币 -> 日历 -> Beszel -> Telegram
    page_functions = [draw_clock, draw_tracking, draw_bilibili, draw_crypto, draw_calendar, draw_beszel, draw_telegram]
    last_displayed_page = -1
    cached_image = None
    
    try:
        last_auto_switch = time.time()
        error_count = 0
        last_redraw_time = 0
        REDRAW_INTERVAL = 1.0  # 每秒重绘一次页面内容
        
        while True:
            try:
                current_page = button_state.get_page()
                current_time = time.time()
                
                if 0 <= current_page < len(page_functions):
                    # 只在需要时重绘页面（每秒一次或页面变化时）
                    need_redraw = (
                        cached_image is None or
                        last_displayed_page != current_page or
                        current_time - last_redraw_time >= REDRAW_INTERVAL
                    )
                    
                    if need_redraw:
                        try:
                            img = page_functions[current_page]()
                            if img:
                                display_image(img)
                                cached_image = img
                                last_displayed_page = current_page
                                last_redraw_time = current_time
                                error_count = 0
                        except Exception as page_error:
                            error_count += 1
                            logger.error(f"页面 {current_page} 绘制失败: {page_error}")
                            
                            if error_count >= max_errors:
                                logger.warning(f"页面错误过多，重置到首页")
                                button_state.current_page = 0
                                error_count = 0
                            elif current_page != 0:
                                button_state.current_page = 0
                                logger.info("页面出错，重置到首页")
                else:
                    logger.warning(f"无效页面索引: {current_page}, 重置到0")
                    button_state.current_page = 0
                
                # 自动页面切换（仅用于测试）
                if AUTO_PAGE_SWITCH_ENABLED:
                    if current_time - last_auto_switch >= AUTO_PAGE_SWITCH_INTERVAL:
                        old_page = button_state.get_page()
                        button_state.next_page()
                        new_page = button_state.get_page()
                        logger.info(f"自动页面切换: {old_page} -> {new_page}")
                        last_auto_switch = current_time
                
                time.sleep(0.02)  # 20ms检查间隔，快速响应按钮
                
            except Exception as loop_error:
                error_count += 1
                logger.error(f"显示循环内部异常: {loop_error}")
                
                # 如果错误太多，尝试重新初始化显示器
                if error_count >= max_errors:
                    logger.warning("尝试重新初始化显示器")
                    try:
                        init_display()
                        error_count = 0
                    except:
                        logger.error("显示器重新初始化失败")
                
                time.sleep(1)  # 出错时等待更长时间
                
    except KeyboardInterrupt:
        logger.info("接收到中断信号，正在退出...")
    except Exception as e:
        logger.error(f"主循环异常: {e}", exc_info=True)
    finally:
        logger.info("系统退出")


if __name__ == "__main__":
    main()