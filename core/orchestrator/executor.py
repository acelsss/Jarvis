"""Execution logic."""
from typing import Dict, Any

from core.contracts.task import Task
from core.contracts.tool import Tool


class Executor:
    """执行器。"""
    
    async def execute(self, task: Task, tool: Tool, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行任务。
        
        Args:
            task: 任务对象
            tool: 工具对象
            params: 执行参数
            
        Returns:
            执行结果
        """
        task.update_status("running")
        
        try:
            result = await tool.execute(params or {})
            task.update_status("completed")
            return {
                "success": True,
                "result": result,
                "task_id": task.task_id,
            }
        except Exception as e:
            task.update_status("failed")
            return {
                "success": False,
                "error": str(e),
                "task_id": task.task_id,
            }
