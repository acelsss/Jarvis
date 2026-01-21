"""Tool result contract definition."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ToolResult:
    """工具执行结果。"""
    
    tool_id: str
    step_id: str
    success: bool
    result: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    evidence_refs: List[str] = field(default_factory=list)  # 证据引用（如生成的文件路径）
    executed_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "tool_id": self.tool_id,
            "step_id": self.step_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "evidence_refs": self.evidence_refs,
            "executed_at": self.executed_at.isoformat(),
        }
