"""Task contract definition."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, List


# 任务状态枚举
TASK_STATUS_NEW = "new"
TASK_STATUS_CONTEXT_BUILT = "context_built"
TASK_STATUS_PLANNED = "planned"
TASK_STATUS_WAITING_APPROVAL = "waiting_approval"
TASK_STATUS_APPROVED = "approved"
TASK_STATUS_RUNNING = "running"
TASK_STATUS_COMPLETED = "completed"
TASK_STATUS_FAILED = "failed"


@dataclass
class Task:
    """任务契约定义。"""
    
    task_id: str
    description: str
    status: str = TASK_STATUS_NEW
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)  # 产物路径列表
    actions: List[Dict[str, Any]] = field(default_factory=list)  # 执行的动作记录
    
    def update_status(self, new_status: str) -> None:
        """更新任务状态。"""
        self.status = new_status
        self.updated_at = datetime.now()
    
    def add_artifact(self, artifact_path: str) -> None:
        """添加产物路径。"""
        if artifact_path not in self.artifacts:
            self.artifacts.append(artifact_path)
    
    def add_action(self, action: Dict[str, Any]) -> None:
        """添加动作记录。"""
        self.actions.append(action)
