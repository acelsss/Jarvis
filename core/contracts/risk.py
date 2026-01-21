"""Risk contract definition."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


# 风险等级枚举
RISK_LEVEL_R0 = "R0"  # 无风险
RISK_LEVEL_R1 = "R1"  # 低风险
RISK_LEVEL_R2 = "R2"  # 中风险，需要审批
RISK_LEVEL_R3 = "R3"  # 高风险，需要审批


@dataclass
class RiskAssessment:
    """风险评估结果。"""
    
    risk_level: str  # R0, R1, R2, R3
    requires_approval: bool
    assessed_at: datetime = None
    reason: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理。"""
        if self.assessed_at is None:
            self.assessed_at = datetime.now()
    
    def is_approval_required(self) -> bool:
        """检查是否需要审批（R2及以上）。"""
        return self.risk_level in (RISK_LEVEL_R2, RISK_LEVEL_R3)


@dataclass
class Approval:
    """审批记录。"""
    
    approval_id: str
    task_id: str
    approved: bool
    approved_at: datetime = None
    approver: Optional[str] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理。"""
        if self.approved_at is None:
            self.approved_at = datetime.now()
