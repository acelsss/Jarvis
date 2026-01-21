"""Execution logic.

注意：v0.1.1 中 Executor 不作为主路径使用。
当前主流程使用 ToolRunner 直接执行工具，Executor 保留为内部 stub 供未来扩展。
"""
from typing import Dict, Any

from core.contracts.task import (
    Task,
    TASK_STATUS_RUNNING,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
)
from core.contracts.tool import Tool


class Executor:
    """执行器。
    
    注意：v0.1.1 中不作为主路径使用，当前主流程使用 ToolRunner。
    保留此 stub 供未来扩展使用。
    """
    
    async def execute(self, task: Task, tool: Tool, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行任务。
        
        Args:
            task: 任务对象
            tool: 工具对象
            params: 执行参数
            
        Returns:
            执行结果
        """
        task.update_status(TASK_STATUS_RUNNING)
        
        try:
            result = await tool.execute(params or {})
            task.update_status(TASK_STATUS_COMPLETED)
            return {
                "success": True,
                "result": result,
                "task_id": task.task_id,
            }
        except Exception as e:
            task.update_status(TASK_STATUS_FAILED)
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id,
            }
