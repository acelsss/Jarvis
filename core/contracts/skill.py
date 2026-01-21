"""Skill contract definition."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlanStep:
    """计划步骤。"""
    
    step_id: str
    tool_id: str
    description: str
    params: Dict[str, Any] = None
    risk_level: str = "R1"
    
    def __post_init__(self):
        """初始化后处理。"""
        if self.params is None:
            self.params = {}


@dataclass
class Plan:
    """执行计划。"""
    
    plan_id: str
    steps: List[PlanStep]
    estimated_duration: Optional[int] = None  # 秒
    source: Optional[str] = None  # 计划来源（如 skill_id）


@dataclass
class JarvisSkill:
    """Jarvis 技能定义（从 SKILL.md 解析）。"""
    
    skill_id: str
    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    instructions_md: str = ""  # Markdown 格式的指令
    metadata: Dict[str, Any] = field(default_factory=dict)  # YAML frontmatter 中的其他字段
    file_path: Optional[str] = None  # SKILL.md 文件路径
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "instructions_md": self.instructions_md,
            "metadata": self.metadata,
            "file_path": self.file_path,
        }


@dataclass
class Skill:
    """技能契约定义。"""
    
    skill_id: str
    name: str
    description: str
    config: Dict[str, Any] = None
    
    async def plan(self, task) -> Plan:
        """将任务转换为执行计划。"""
        # TODO: 由具体技能实现
        raise NotImplementedError
