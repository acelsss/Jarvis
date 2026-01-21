"""Planning logic."""
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.contracts.task import Task
from core.contracts.skill import Plan, PlanStep
from core.contracts.risk import RISK_LEVEL_R1, RISK_LEVEL_R2
from core.utils.ids import generate_id


class Planner:
    """计划器。"""
    
    def __init__(self, sandbox_root: str = "./sandbox"):
        """初始化计划器。
        
        Args:
            sandbox_root: 沙箱根目录
        """
        self.sandbox_root = sandbox_root
    
    async def create_plan(
        self,
        task: Task,
        available_tools: Dict[str, Any] = None,
        routed_tools: List[str] = None,
    ) -> Plan:
        """为任务创建执行计划（生成2-3个步骤，至少包含一个file_tool）。
        
        Args:
            task: 任务对象
            available_tools: 可用工具字典
            routed_tools: 路由后的工具ID列表
            
        Returns:
            执行计划
        """
        plan_id = generate_id("plan")
        steps: List[PlanStep] = []
        
        # 确保至少有一个 file_tool 步骤
        has_file_tool = False
        if routed_tools and "file" in routed_tools:
            has_file_tool = True
        
        # 步骤1: 总是创建一个文件作为 artifact
        if "file" in (available_tools or {}):
            step1 = PlanStep(
                step_id=generate_id("step"),
                tool_id="file",
                description=f"创建任务产物文件: {task.task_id}.txt",
                params={
                    "operation": "write",
                    "path": f"{self.sandbox_root}/{task.task_id}.txt",
                    "content": f"任务: {task.description}\n创建时间: {datetime.now().isoformat()}\n任务ID: {task.task_id}",
                },
                risk_level=RISK_LEVEL_R1,
            )
            steps.append(step1)
            has_file_tool = True
        
        # 步骤2: 如果路由到其他工具，添加一个步骤
        if routed_tools:
            for tool_id in routed_tools[:2]:  # 最多2个其他工具
                if tool_id == "file" and has_file_tool:
                    continue
                if tool_id in (available_tools or {}):
                    # 根据工具类型设置合适的参数
                    if tool_id == "shell":
                        params = {"command": f"echo '处理任务: {task.description}'"}
                        risk_level = RISK_LEVEL_R2
                    else:
                        # 其他工具使用通用参数
                        params = {"operation": "info", "message": f"处理任务: {task.description}"}
                        risk_level = RISK_LEVEL_R1
                    
                    step = PlanStep(
                        step_id=generate_id("step"),
                        tool_id=tool_id,
                        description=f"执行工具: {tool_id}",
                        params=params,
                        risk_level=risk_level,
                    )
                    steps.append(step)
                    if len(steps) >= 3:
                        break
        
        # 如果还没有 file_tool，强制添加一个
        if not has_file_tool and "file" in (available_tools or {}):
            step_file = PlanStep(
                step_id=generate_id("step"),
                tool_id="file",
                description=f"创建任务产物文件: {task.task_id}_artifact.txt",
                params={
                    "operation": "write",
                    "path": f"{self.sandbox_root}/{task.task_id}_artifact.txt",
                    "content": f"任务产物\n任务: {task.description}\n创建时间: {datetime.now().isoformat()}",
                },
                risk_level=RISK_LEVEL_R1,
            )
            steps.insert(0, step_file)
        
        # 确保至少有2个步骤
        if len(steps) < 2 and "file" in (available_tools or {}):
            step2 = PlanStep(
                step_id=generate_id("step"),
                tool_id="file",
                description=f"创建任务摘要文件: {task.task_id}_summary.txt",
                params={
                    "operation": "write",
                    "path": f"{self.sandbox_root}/{task.task_id}_summary.txt",
                    "content": f"任务摘要\n任务ID: {task.task_id}\n描述: {task.description}\n状态: {task.status}",
                },
                risk_level=RISK_LEVEL_R1,
            )
            steps.append(step2)
        
        return Plan(plan_id=plan_id, steps=steps, estimated_duration=len(steps) * 10)
