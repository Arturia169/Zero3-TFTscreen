# 🖥️ 香橙派智能屏幕系统

<div align="center">

![Platform](https://img.shields.io/badge/Platform-Orange%20Pi%20Zero%203-orange)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED)
![License](https://img.shields.io/badge/License-MIT-green)

一个运行在香橙派 Zero 3 上的多功能智能屏幕显示系统，支持时钟、天气、加密货币、物流追踪、B站监控等多种功能。

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [配置说明](#️-配置说明) • [架构设计](#-架构设计) • [开发指南](#-开发指南)

</div>

---

## ✨ 功能特性

### 📊 多页面显示

- **🕐 Nixie 管时钟** - 复古辉光管风格的时钟显示，带日期、农历和生活指数
- **💰 加密货币监控** - 实时显示 BTC、ETH、DOGE 价格和涨跌幅
- **📅 日历倒数日** - 重要日期倒数提醒
- **📦 物流追踪** - 快递包裹实时追踪
- **🎮 B站监控** - 关注主播的直播状态监控
- **🖥️ 服务器监控** - Beszel 服务器性能监控
- **💬 Telegram 消息** - 频道消息实时推送

### 🎨 UI 特性

- **动态主题** - 根据时间自动切换色调（清晨、上午、下午、傍晚、夜晚、深夜）
- **夜间模式** - 01:30-08:00 自动降低亮度
- **流畅动画** - 渐变背景和平滑过渡效果
- **高性能渲染** - NumPy 向量化像素转换，CPU 占用率低至 13-35%

### 🔧 技术亮点

- **模块化架构** - 清晰的代码组织，易于维护和扩展
- **Docker 部署** - 一键部署，支持多架构（ARM64/AMD64）
- **配置热加载** - 修改配置文件无需重启
- **Web 管理界面** - 远程管理和配置
- **多线程更新** - 7 个独立的后台工作线程

---

## 🚀 快速开始

### 前置要求

- 香橙派 Zero 3（或其他支持 SPI 的 ARM 设备）
- ST7789 驱动的 320x240 TFT 屏幕
- Docker 和 Docker Compose
- 已启用 SPI 接口

### 一键部署

```bash
# 1. 克隆项目
git clone https://github.com/Arturia169/Zero3-TFTscreen.git
cd Zero3-TFTscreen

# 2. 启动容器
docker compose up -d

# 3. 查看日志
docker compose logs -f
```

### 手动运行（开发模式）

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

---

## ⚙️ 配置说明

### 配置文件

主配置文件位于 `screen/config/default.yaml`，支持以下配置：

```yaml
# 天气配置
weather:
  api_key: "your-api-key"
  city_id: "101130601"
  update_interval: 1800

# 硬件配置
hardware:
  display:
    width: 320
    height: 240
  spi:
    max_speed: 62500000

# 显示配置
display:
  refresh_interval: 1.0
  night_mode:
    enabled: true
    start_hour: 1
    start_minute: 30
    end_hour: 8
    brightness_factor: 0.3
```

### 环境变量

通过 `docker-compose.yml` 配置代理：

```yaml
environment:
  - http_proxy=http://192.168.5.100:7890
  - https_proxy=http://192.168.5.100:7890
```

---

## 🏗️ 架构设计

### 项目结构

```
screen/
├── core/              # 核心模块
│   ├── config.py      # 配置管理
│   ├── data_store.py  # 数据存储
│   └── display.py     # 硬件驱动
├── workers/           # 后台工作线程
│   ├── base.py        # Worker 基类
│   ├── weather.py     # 天气更新
│   ├── system.py      # 系统监控
│   ├── crypto.py      # 加密货币
│   └── ...
├── ui/                # UI 渲染
│   ├── themes.py      # 主题系统
│   ├── components.py  # 公共组件
│   └── pages/         # 页面模块
│       ├── clock.py
│       ├── crypto.py
│       └── ...
├── web/               # Web API
│   └── api.py
├── utils/             # 工具函数
│   ├── logger.py
│   └── hotreload.py
└── config/            # 配置文件
    └── default.yaml
```

### 技术栈

- **语言**: Python 3.10+
- **硬件通信**: SpiDev (SPI), Sysfs (GPIO)
- **图像处理**: Pillow, NumPy
- **容器化**: Docker, Docker Compose
- **CI/CD**: GitHub Actions
- **配置管理**: PyYAML

### 性能优化

1. **NumPy 向量化** - 像素转换速度提升 50-100 倍
2. **全局素材缓存** - 避免重复磁盘 I/O
3. **智能刷新** - 仅在需要时重绘页面
4. **多线程架构** - 数据更新和渲染分离

---

## 👨‍💻 开发指南

### 添加新页面

1. 在 `screen/ui/pages/` 创建新文件：

```python
# screen/ui/pages/my_page.py
from PIL import Image, ImageDraw
from ..themes import create_dynamic_background

def render(data_store, fonts, **kwargs) -> Image.Image:
    img = create_dynamic_background()
    draw = ImageDraw.Draw(img)
    # 你的绘图逻辑
    return img
```

2. 在 `screen/ui/pages/__init__.py` 中注册：

```python
from . import my_page

def get_all_pages():
    return [
        # ...
        my_page.render,
    ]
```

### 添加新 Worker

1. 创建 Worker 类：

```python
# screen/workers/my_worker.py
from .base import BaseWorker

class MyWorker(BaseWorker):
    def update(self):
        # 你的数据更新逻辑
        self.data_store.update({"key": "value"})
```

2. 在 `screen/workers/__init__.py` 中注册：

```python
from .my_worker import MyWorker

def create_all_workers(data_store, config, logger):
    return [
        # ...
        MyWorker(data_store, 60, config, logger),
    ]
```

### 本地测试

```bash
# 测试基础模块
python test_modules.py

# 运行主程序
python main.py
```

---

## 📸 截图展示

> TODO: 添加实际运行截图

---

## 🔄 更新日志

### v2.0.0 (2026-01-19)

- ✨ 完成模块化重构
- ⚡ 性能优化：CPU 占用率从 76% 降至 13-35%
- 🎨 新增动态主题系统
- 📦 Docker 多架构支持
- 🔧 配置文件化管理

### v1.0.0

- 🎉 初始版本发布

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [Orange Pi](http://www.orangepi.org/) - 硬件平台
- [Pillow](https://python-pillow.org/) - 图像处理库
- [NumPy](https://numpy.org/) - 数值计算库

---

## 📞 联系方式

- GitHub: [@Arturia169](https://github.com/Arturia169)
- 项目链接: [https://github.com/Arturia169/Zero3-TFTscreen](https://github.com/Arturia169/Zero3-TFTscreen)

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐ Star 支持一下！**

Made with ❤️ by Arturia169

</div>
