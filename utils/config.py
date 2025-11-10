"""
配置管理模块
"""
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class Settings:
    OPENMEMORY_BASE_URL: str = "http://localhost:8000"
    OPENMEMORY_API_KEY: Optional[str] = None
    
    @classmethod
    def load(cls) -> "Settings":
        """从环境变量或默认值加载配置"""
        return cls(
            OPENMEMORY_BASE_URL=os.getenv("OPENMEMORY_BASE_URL", "http://localhost:8000"),
            OPENMEMORY_API_KEY=os.getenv("OPENMEMORY_API_KEY")
        )

