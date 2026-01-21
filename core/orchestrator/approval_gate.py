"""Approval gate logic."""
from typing import List

from core.contracts.task import Task
from core.contracts.risk import RiskAssessment, Approval, RISK_LEVEL_R2, RISK_LEVEL_R3
from core.contracts.skill import PlanStep
from core.utils.ids import generate_id


class ApprovalGate:
    """审批门控。"""
    
    def assess_plan_risk(self, steps: List[PlanStep]) -> RiskAssessment:
        """评估计划风险（检查是否有R2及以上风险等级）。
        
        Args:
            steps: 计划步骤列表
            
        Returns:
            风险评估结果
        """
        max_risk = "R0"
        for step in steps:
            if step.risk_level in (RISK_LEVEL_R2, RISK_LEVEL_R3):
                max_risk = step.risk_level
                break
            elif step.risk_level > max_risk:
                max_risk = step.risk_level
        
        requires_approval = max_risk in (RISK_LEVEL_R2, RISK_LEVEL_R3)
        
        return RiskAssessment(
            risk_level=max_risk,
            requires_approval=requires_approval,
            reason=f"Plan contains steps with risk level: {max_risk}",
        )
    
    def assess_risk(self, task: Task, tool_risk_level: str) -> RiskAssessment:
        """评估任务风险。
        
        Args:
            task: 任务对象
            tool_risk_level: 工具风险等级
            
        Returns:
            风险评估结果
        """
        requires_approval = tool_risk_level in (RISK_LEVEL_R2, RISK_LEVEL_R3)
        return RiskAssessment(
            risk_level=tool_risk_level,
            requires_approval=requires_approval,
            reason=f"Tool risk level: {tool_risk_level}",
        )
    
    def approve(self, task_id: str, approved: bool = True, approver: str = None) -> Approval:
        """审批任务。
        
        Args:
            task_id: 任务ID
            approved: 是否批准
            approver: 审批人
            
        Returns:
            审批记录
        """
        approval_id = generate_id("approval")
        return Approval(
            approval_id=approval_id,
            task_id=task_id,
            approved=approved,
            approver=approver or "user",
        )
    
    def check_approval_required(self, risk_assessment: RiskAssessment) -> bool:
        """检查是否需要审批。"""
        return risk_assessment.is_approval_required()
