"""
Memory 数据类型定义
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

@dataclass
class MemoryItem:
    """记忆项"""
    type: str
    content: str
    timestamp: str
    source: Optional[Dict[str, Any]] = None
    entities: Optional[List[str]] = None
    importance: Optional[float] = None
    extras: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        d = asdict(self)
        # 移除 None 值
        return {k: v for k, v in d.items() if v is not None}

@dataclass
class SearchResult:
    """搜索结果"""
    id: Optional[str] = None
    type: Optional[str] = None
    content: str = ""
    timestamp: Optional[str] = None  # 格式化的时间字符串（YYYY-MM-DD HH:MM）
    score: Optional[float] = None
    source: Optional[Dict[str, Any]] = None
    extras: Optional[Dict[str, Any]] = None
    raw: Optional[Dict[str, Any]] = None  # 原始响应数据（包含原始时间戳等）

def make_memory_item(
    content: str,
    default_type: str = "note",
    source_app: str = "Jarvis",
    channel: str = "cli",
    tags: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> MemoryItem:
    """
    创建记忆项的辅助函数
    
    Args:
        content: 内容文本
        default_type: 默认类型
        source_app: 来源应用
        channel: 渠道
        tags: 标签列表
    
    Returns:
        MemoryItem 实例
    """
    if tags is None:
        tags = ["jarvis", "v1"]
    
    # 生成 ISO8601 timestamp (UTC)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    
    source = {
        "app": source_app,
        "channel": channel,
        "tags": tags
    }
    
    return MemoryItem(
        type=default_type,
        content=content,
        timestamp=timestamp,
        source=source,
        entities=None,
        importance=None,
        extras=metadata if metadata else None  # 将 metadata 存储在 extras 中
    )


@dataclass
class StoreResult:
    """存储结果"""
    status: str  # "new" 或 "dedup"
    node_id: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

