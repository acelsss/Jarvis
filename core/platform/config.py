"""Configuration management."""
import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


class Config:
    """配置管理器。"""
    
    def __init__(self, config_dir: str = "./identity_pack"):
        """初始化配置管理器。"""
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Any] = {}
    
    def load_yaml(self, filename: str) -> Dict[str, Any]:
        """加载 YAML 配置文件。"""
        if filename in self._cache:
            return self._cache[filename]
        
        file_path = self.config_dir / filename
        if not file_path.exists():
            return {}
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        self._cache[filename] = data
        return data
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值（从环境变量或配置文件）。"""
        # 优先从环境变量读取
        value = os.getenv(key)
        if value is not None:
            return value
        return default
