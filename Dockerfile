# 使用官方 Python 轻量级镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖（包含 SPI、GPIO、Pillow 编译依赖以及中文字体包）
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 环境变量设置
ENV PYTHONUNBUFFERED=1
ENV DISPLAY_PAGES=7

# 启动命令
CMD ["python", "main.py"]
