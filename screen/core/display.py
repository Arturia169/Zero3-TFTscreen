"""显示器硬件驱动模块"""
import os
import time
import numpy as np
from PIL import Image
from typing import Optional


class DisplayDriver:
    """ST7789 显示器驱动类"""
    
    def __init__(self, config=None, logger=None):
        """
        初始化显示驱动
        
        Args:
            config: 配置对象
            logger: 日志记录器
        """
        self._logger = logger
        self._spi = None
        
        # 从配置读取参数，或使用默认值
        if config:
            self.width = config.get("hardware.display.width", 320)
            self.height = config.get("hardware.display.height", 240)
            self.dc_pin = config.get("hardware.display.dc_pin", "75")
            self.rst_pin = config.get("hardware.display.rst_pin", "79")
            self.cs_pin = config.get("hardware.display.cs_pin", "233")
            self.button_pin = config.get("hardware.button.pin", "70")
            self.spi_bus = config.get("hardware.spi.bus", 1)
            self.spi_device = config.get("hardware.spi.device", 0)
            self.spi_speed = config.get("hardware.spi.max_speed", 62500000)
        else:
            # 默认值
            self.width = 320
            self.height = 240
            self.dc_pin = "75"
            self.rst_pin = "79"
            self.cs_pin = "233"
            self.button_pin = "70"
            self.spi_bus = 1
            self.spi_device = 0
            self.spi_speed = 62500000
    
    def _log(self, level: str, message: str):
        """内部日志方法"""
        if self._logger:
            getattr(self._logger, level)(message)
        else:
            print(f"[{level.upper()}] {message}")
    
    # ========== GPIO 操作 ==========
    
    def gpio_set(self, pin: str, value: int) -> None:
        """设置GPIO引脚值"""
        try:
            os.system(f"echo {value} > /sys/class/gpio/gpio{pin}/value 2>/dev/null")
        except Exception as e:
            self._log('warning', f"GPIO设置失败 pin={pin}, value={value}: {e}")
    
    def init_gpio(self, pin: str, direction: str = "out") -> bool:
        """初始化GPIO引脚"""
        try:
            gpio_path = f"/sys/class/gpio/gpio{pin}"
            if not os.path.exists(gpio_path):
                os.system(f"echo {pin} > /sys/class/gpio/export 2>/dev/null")
            time.sleep(0.1)
            os.system(f"echo {direction} > {gpio_path}/direction 2>/dev/null")
            return True
        except Exception as e:
            self._log('error', f"GPIO初始化失败 pin={pin}: {e}")
            return False
    
    def init_button_gpio(self) -> bool:
        """初始化按键GPIO"""
        return self.init_gpio(self.button_pin, "in")
    
    def read_button_raw(self) -> bool:
        """读取按键原始状态"""
        try:
            with open(f"/sys/class/gpio/gpio{self.button_pin}/value", "r") as f:
                return f.read().strip() == "0"
        except Exception as e:
            self._log('debug', f"读取按键失败: {e}")
            return False
    
    # ========== SPI 操作 ==========
    
    def init_spi(self) -> bool:
        """初始化SPI"""
        try:
            import spidev
            self._spi = spidev.SpiDev()
            self._spi.open(self.spi_bus, self.spi_device)
            self._spi.max_speed_hz = self.spi_speed
            self._spi.mode = 0
            self._log('info', "SPI初始化成功")
            return True
        except Exception as e:
            self._log('error', f"SPI初始化失败: {e}")
            self._spi = None
            return False
    
    def write_cmd(self, cmd: int) -> None:
        """写入命令到显示器"""
        if self._spi is None:
            return
        try:
            self.gpio_set(self.cs_pin, 0)
            self.gpio_set(self.dc_pin, 0)
            self._spi.writebytes([cmd])
            self.gpio_set(self.cs_pin, 1)
        except Exception as e:
            self._log('error', f"写入命令失败 cmd=0x{cmd:02X}: {e}")
    
    def write_data(self, data) -> None:
        """写入数据到显示器"""
        if self._spi is None:
            return
        try:
            self.gpio_set(self.cs_pin, 0)
            self.gpio_set(self.dc_pin, 1)
            if isinstance(data, int):
                self._spi.writebytes([data])
            else:
                self._spi.writebytes(list(data))
            self.gpio_set(self.cs_pin, 1)
        except Exception as e:
            self._log('error', f"写入数据失败: {e}")
    
    # ========== 显示器初始化 ==========
    
    def init_display(self) -> bool:
        """初始化显示器"""
        try:
            # 初始化按键GPIO
            self.init_button_gpio()
            
            # 初始化显示器控制GPIO
            for pin in [self.dc_pin, self.rst_pin, self.cs_pin]:
                if not self.init_gpio(pin, "out"):
                    self._log('error', f"显示器GPIO初始化失败: {pin}")
                    return False
            
            # 初始化SPI
            if not self.init_spi():
                return False
            
            # 硬件复位
            self.gpio_set(self.rst_pin, 0)
            time.sleep(0.1)
            self.gpio_set(self.rst_pin, 1)
            time.sleep(0.1)
            
            # 初始化序列
            self.write_cmd(0x01)  # Software reset
            time.sleep(0.1)
            self.write_cmd(0x11)  # Sleep out
            time.sleep(0.1)
            self.write_cmd(0x36)  # Memory access control
            self.write_data(0x28)
            self.write_cmd(0x3A)  # Pixel format
            self.write_data(0x55)  # 16-bit RGB565
            self.write_cmd(0x29)  # Display on
            
            self._log('info', "显示器初始化成功")
            import sys
            sys.stdout.flush()
            sys.stderr.flush()
            return True
        except Exception as e:
            self._log('error', f"显示器初始化失败: {e}")
            return False
    
    # ========== 图像处理 ==========
    
    @staticmethod
    def rgb_to_rgb565(r: int, g: int, b: int) -> int:
        """将RGB888转换为RGB565格式"""
        return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    
    def image_to_rgb565_bytes(self, image: Image.Image) -> bytes:
        """使用 NumPy 向量化操作将 PIL 图像转换为 RGB565 字节数组"""
        # 确保图像为 RGB 模式并转换为 numpy 数组
        img_array = np.array(image.convert("RGB"), dtype=np.uint16)
        
        # 提取 R, G, B 通道
        r = img_array[:, :, 0]
        g = img_array[:, :, 1]
        b = img_array[:, :, 2]
        
        # 转换为 RGB565
        rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        
        # 将 16 位整数数组转换为大端序字节
        return rgb565.byteswap().tobytes()
    
    def display_image(self, image: Image.Image) -> None:
        """在显示器上显示图像"""
        if self._spi is None:
            return
        
        try:
            # 设置显示窗口
            self.write_cmd(0x2A)  # Column address set
            self.write_data([0x00, 0x00, 0x01, 0x3F])
            self.write_cmd(0x2B)  # Row address set
            self.write_data([0x00, 0x00, 0x00, 0xEF])
            self.write_cmd(0x2C)  # Memory write
            
            self.gpio_set(self.cs_pin, 0)
            self.gpio_set(self.dc_pin, 1)
            
            # 转换并发送像素数据
            pixels = self.image_to_rgb565_bytes(image)
            self._spi.writebytes2(pixels)
            
            self.gpio_set(self.cs_pin, 1)
        except Exception as e:
            self._log('error', f"显示图像失败: {e}")
            # 尝试重新初始化SPI
            try:
                if self._spi:
                    self._spi.close()
                time.sleep(0.1)
                self.init_display()
            except:
                pass
    
    def clear_display(self) -> None:
        """清空显示器"""
        if self._spi is None:
            return
        try:
            self.write_cmd(0x2C)  # Memory write
            self.gpio_set(self.cs_pin, 0)
            self.gpio_set(self.dc_pin, 1)
            # 发送全黑数据
            self._spi.writebytes2(bytearray(self.width * self.height * 2))
            self.gpio_set(self.cs_pin, 1)
        except Exception as e:
            self._log('error', f"清空显示器失败: {e}")
    
    def close(self) -> None:
        """关闭SPI连接"""
        if self._spi:
            try:
                self._spi.close()
                self._log('info', "SPI连接已关闭")
            except:
                pass


# 向后兼容的全局函数（供 main.py 过渡使用）
_global_driver: Optional[DisplayDriver] = None


def init_global_driver(config=None, logger=None) -> DisplayDriver:
    """初始化全局驱动实例"""
    global _global_driver
    _global_driver = DisplayDriver(config, logger)
    return _global_driver


def get_global_driver() -> Optional[DisplayDriver]:
    """获取全局驱动实例"""
    return _global_driver
