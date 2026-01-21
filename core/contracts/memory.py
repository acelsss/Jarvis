"""Memory contract definition."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Memory:
    """记忆契约定义。"""
    
    memory_id: str
    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "memory_id": self.memory_id,
            "content": self.content,
            "metadata": self.metadata,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }
