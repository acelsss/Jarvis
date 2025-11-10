"""
配置管理模块
"""
from dataclasses import dataclass
from typing import Optional, List
import os

@dataclass
class OpenMemoryConfig:
    """OpenMemory 配置"""
    base_url: str = "http://127.0.0.1:8081"
    api_key: Optional[str] = None
    source: str = "Jarvis"
    timeout_ms: int = 8000
    store_default_type: str = "note"
    search_limit: int = 5
    exclude_types: List[str] = None
    endpoint_store: Optional[str] = None
    endpoint_search: Optional[str] = None
    
    def __post_init__(self):
        if self.exclude_types is None:
            self.exclude_types = ["transient"]

@dataclass
class LLMConfig:
    """LLM 配置"""
    provider: str = "deepseek"
    deepseek_api_key: Optional[str] = None
    deepseek_base_url: Optional[str] = None

@dataclass
class Settings:
    OPENMEMORY_BASE_URL: str = "http://localhost:8000"
    OPENMEMORY_API_KEY: Optional[str] = None
    om: OpenMemoryConfig = None
    llm: LLMConfig = None
    
    @classmethod
    def load(cls) -> "Settings":
        """从环境变量或默认值加载配置"""
        # 解析 OM_EXCLUDE_TYPES（逗号分隔字符串转列表）
        exclude_types_str = os.getenv("OM_EXCLUDE_TYPES", "transient")
        exclude_types = [t.strip() for t in exclude_types_str.split(",") if t.strip()]
        
        om_config = OpenMemoryConfig(
            base_url=os.getenv("OM_BASE_URL", "http://127.0.0.1:8081"),
            api_key=os.getenv("OM_API_KEY"),
            source=os.getenv("OM_SOURCE", "Jarvis"),
            timeout_ms=int(os.getenv("OM_TIMEOUT_MS", "8000")),
            store_default_type=os.getenv("OM_STORE_DEFAULT_TYPE", "note"),
            search_limit=int(os.getenv("OM_SEARCH_LIMIT", "5")),
            exclude_types=exclude_types,
            endpoint_store=os.getenv("OM_ENDPOINT_STORE") or None,
            endpoint_search=os.getenv("OM_ENDPOINT_SEARCH") or None
        )
        
        llm_config = LLMConfig(
            provider=os.getenv("LLM_PROVIDER", "deepseek"),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL") or None
        )
        
        return cls(
            OPENMEMORY_BASE_URL=om_config.base_url,  # 保持向后兼容
            OPENMEMORY_API_KEY=om_config.api_key,    # 保持向后兼容
            om=om_config,
            llm=llm_config
        )

