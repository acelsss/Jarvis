"""Task management."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

from core.contracts.task import Task
from core.utils.ids import generate_id
from core.utils.fs import ensure_dir


class TaskManager:
    """任务管理器。"""
    
    def __init__(self, task_db_path: str = "./memory/task_db/tasks.jsonl"):
        """初始化任务管理器。
        
        Args:
            task_db_path: 任务数据库文件路径（JSONL格式）
        """
        self.tasks: Dict[str, Task] = {}
        self.task_db_path = Path(task_db_path)
        # 确保目录存在
        ensure_dir(self.task_db_path.parent)
    
    def _task_to_dict(self, task: Task, extra_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """将任务转换为可序列化的字典。
        
        Args:
            task: 任务对象
            extra_info: 额外信息（plan, skill_id, approval 等）
            
        Returns:
            可序列化的字典
        """
        task_dict = {
            "task_id": task.task_id,
            "description": task.description,
            "status": task.status,
            "created_at": task.created_at.isoformat() if isinstance(task.created_at, datetime) else str(task.created_at),
            "updated_at": task.updated_at.isoformat() if isinstance(task.updated_at, datetime) else str(task.updated_at),
            "artifacts": task.artifacts,
            "actions_count": len(task.actions),
        }
        
        # 添加额外信息
        if extra_info:
            # 处理 plan（如果是 dataclass，转换为 dict）
            if "plan" in extra_info and extra_info["plan"]:
                plan = extra_info["plan"]
                if hasattr(plan, "__dict__"):
                    # 使用 plan_to_dict 确保 JSON-safe
                    try:
                        from skills.runtime.to_plan import plan_to_dict
                        plan_dict = plan_to_dict(plan)
                    except ImportError:
                        # 如果导入失败，使用降级方案
                        plan_dict = {
                            "plan_id": getattr(plan, "plan_id", None),
                            "source": getattr(plan, "source", None),
                            "steps_count": len(getattr(plan, "steps", [])),
                            "steps": [
                                {
                                    "step_id": getattr(step, "step_id", None),
                                    "tool_id": getattr(step, "tool_id", None),
                                    "description": getattr(step, "description", None),
                                    "risk_level": getattr(step, "risk_level", None),
                                }
                                for step in getattr(plan, "steps", [])
                            ] if hasattr(plan, "steps") else [],
                        }
                    task_dict["plan"] = plan_dict
                else:
                    task_dict["plan"] = extra_info["plan"]
            
            # 添加其他额外信息
            for key in ["skill_id", "routed_tools", "approval"]:
                if key in extra_info:
                    value = extra_info[key]
                    # 如果是对象，尝试转换为 dict
                    if hasattr(value, "__dict__"):
                        task_dict[key] = {
                            k: v.isoformat() if isinstance(v, datetime) else v
                            for k, v in value.__dict__.items()
                        }
                    elif isinstance(value, datetime):
                        task_dict[key] = value.isoformat()
                    else:
                        task_dict[key] = value
        
        return task_dict
    
    def _save_snapshot(self, task: Task, extra_info: Dict[str, Any] = None) -> None:
        """保存任务快照到文件（追加模式）。
        
        Args:
            task: 任务对象
            extra_info: 额外信息（plan, skill_id, approval 等）
        """
        task_dict = self._task_to_dict(task, extra_info)
        
        # 追加模式写入 JSONL
        with open(self.task_db_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(task_dict, ensure_ascii=False) + "\n")
    
    def create_task(self, description: str, context: Dict = None) -> Task:
        """创建新任务。"""
        task_id = generate_id("task")
        task = Task(
            task_id=task_id,
            description=description,
            context=context or {},
        )
        self.tasks[task_id] = task
        # 保存快照
        self._save_snapshot(task)
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务。"""
        return self.tasks.get(task_id)
    
    def update_task(self, task: Task, extra_info: Dict[str, Any] = None) -> None:
        """更新任务。
        
        Args:
            task: 任务对象
            extra_info: 额外信息（plan, skill_id, approval 等），用于保存快照
        """
        self.tasks[task.task_id] = task
        # 保存快照
        self._save_snapshot(task, extra_info)
