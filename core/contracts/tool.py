"""Tool contract definition."""
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.contracts.risk import RISK_LEVEL_R0, RISK_LEVEL_R1, RISK_LEVEL_R2


@dataclass
class Tool:
    """工具契约定义。"""
    
    tool_id: str
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema
    risk_level: str = RISK_LEVEL_R1  # R0, R1, R2, R3
    requires_approval: bool = False
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具并返回结果。"""
        # TODO: 由具体工具实现
        raise NotImplementedError
