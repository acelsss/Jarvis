"""Secrets management."""
import os
from typing import Optional


class SecretsManager:
    """密钥管理器。"""
    
    @staticmethod
    def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
        """获取密钥（从环境变量）。
        
        Args:
            key: 密钥名称
            default: 默认值
            
        Returns:
            密钥值
        """
        return os.getenv(key, default)
    
    @staticmethod
    def set_secret(key: str, value: str) -> None:
        """设置密钥（仅限运行时，不持久化）。"""
        os.environ[key] = value
