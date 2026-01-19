"""配置管理模块"""
import os
import yaml
from typing import Any, Dict, Optional


class Config:
    """配置管理类"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置
        
        Args:
            config_file: 配置文件路径，None 则使用默认配置
        """
        self._config: Dict[str, Any] = {}
        self._config_file = config_file
        
        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)
        else:
            # 使用默认配置
            default_config = os.path.join(
                os.path.dirname(__file__),
                '..',
                'config',
                'default.yaml'
            )
            if os.path.exists(default_config):
                self.load_from_file(default_config)
    
    def load_from_file(self, file_path: str) -> None:
        """从 YAML 文件加载配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"加载配置文件失败 {file_path}: {e}")
            self._config = {}
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的路径）
        
        Args:
            key_path: 配置键路径，如 "weather.api_key"
            default: 默认值
        
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self._config
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
                if value is None:
                    return default
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """
        设置配置值（支持点号分隔的路径）
        
        Args:
            key_path: 配置键路径
            value: 配置值
        """
        keys = key_path.split('.')
        config = self._config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
    
    def reload(self) -> None:
        """重新加载配置文件"""
        if self._config_file and os.path.exists(self._config_file):
            self.load_from_file(self._config_file)
    
    @property
    def all(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()


def load_config(config_file: Optional[str] = None) -> Config:
    """
    加载配置
    
    Args:
        config_file: 配置文件路径
    
    Returns:
        Config 实例
    """
    return Config(config_file)
