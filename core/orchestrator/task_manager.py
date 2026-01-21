"""Task management."""
from typing import Dict, Optional

from core.contracts.task import Task
from core.utils.ids import generate_id


class TaskManager:
    """任务管理器。"""
    
    def __init__(self):
        """初始化任务管理器。"""
        self.tasks: Dict[str, Task] = {}
    
    def create_task(self, description: str, context: Dict = None) -> Task:
        """创建新任务。"""
        task_id = generate_id("task")
        task = Task(
            task_id=task_id,
            description=description,
            context=context or {},
        )
        self.tasks[task_id] = task
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务。"""
        return self.tasks.get(task_id)
    
    def update_task(self, task: Task) -> None:
        """更新任务。"""
        self.tasks[task.task_id] = task
