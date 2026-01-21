"""Context bundle management."""
from typing import Any, Dict, List


class ContextBundle:
    """上下文包，聚合多个上下文源。"""
    
    def __init__(self):
        """初始化上下文包。"""
        self.contexts: List[Dict[str, Any]] = []
    
    def add_context(self, context: Dict[str, Any]) -> None:
        """添加上下文。"""
        self.contexts.append(context)
    
    def merge(self) -> Dict[str, Any]:
        """合并所有上下文。"""
        merged = {}
        for ctx in self.contexts:
            merged.update(ctx)
        return merged
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取上下文值。"""
        merged = self.merge()
        return merged.get(key, default)
