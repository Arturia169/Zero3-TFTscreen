#!/usr/bin/env python3
"""验证基础模块是否正常工作"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_logger():
    """测试日志模块"""
    print("测试日志模块...")
    from screen.utils.logger import setup_logger
    
    logger = setup_logger("test", log_file=None)
    logger.info("日志模块测试成功！")
    print("✓ 日志模块正常")

def test_data_store():
    """测试数据存储模块"""
    print("\n测试数据存储模块...")
    from screen.core.data_store import DataStore
    
    store = DataStore()
    store.set("test_key", "test_value")
    assert store.get("test_key") == "test_value"
    
    store.update({"key1": "value1", "key2": "value2"})
    assert store["key1"] == "value1"
    
    print("✓ 数据存储模块正常")

def test_config():
    """测试配置模块"""
    print("\n测试配置模块...")
    from screen.core.config import load_config
    
    config = load_config()
    
    # 测试读取默认配置
    weather_key = config.get("weather.api_key")
    print(f"  天气 API Key: {weather_key[:10]}...")
    
    display_width = config.get("hardware.display.width")
    print(f"  显示宽度: {display_width}")
    
    print("✓ 配置模块正常")

def test_hotreload():
    """测试配置热加载模块"""
    print("\n测试配置热加载模块...")
    from screen.utils.hotreload import ConfigReloader
    
    reloader = ConfigReloader()
    print("✓ 配置热加载模块正常")

if __name__ == "__main__":
    print("=" * 50)
    print("基础模块验证测试")
    print("=" * 50)
    
    try:
        test_logger()
        test_data_store()
        test_config()
        test_hotreload()
        
        print("\n" + "=" * 50)
        print("✅ 所有基础模块测试通过！")
        print("=" * 50)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
