"""Routing logic."""
from typing import Dict, Any, List, Optional, Tuple

from core.contracts.task import Task
from core.contracts.skill import JarvisSkill


def route_task(
    task: Task,
    available_tools: Dict[str, Any] = None,
    available_skills: Dict[str, JarvisSkill] = None,
) -> Tuple[Optional[JarvisSkill], List[str]]:
    """路由任务到合适的技能或工具（简单规则路由）。
    
    Args:
        task: 任务对象
        available_tools: 可用工具字典
        available_skills: 可用技能字典
        
    Returns:
        (匹配的技能, 工具ID列表) 元组。如果匹配到技能，技能不为None；否则返回工具列表
    """
    available_tools = available_tools or {}
    available_skills = available_skills or {}
    
    description_lower = task.description.lower()
    
    # 1. 优先检查是否匹配技能（通过关键词或标签）
    for skill in available_skills.values():
        # 检查任务描述是否包含技能名称或标签
        skill_name_lower = skill.name.lower()
        if skill_name_lower in description_lower:
            return (skill, [])
        
        # 检查标签匹配
        for tag in skill.tags:
            if tag.lower() in description_lower:
                return (skill, [])
    
    # 2. 如果没有匹配到技能，使用工具路由
    tool_priority = []
    
    # 检查是否需要文件操作
    file_keywords = ["文件", "写", "创建", "生成", "保存", "file", "write", "create", "generate", "save"]
    if any(keyword in description_lower for keyword in file_keywords):
        if "file" in available_tools:
            tool_priority.append("file")
    
    # 其他工具按顺序添加
    for tool_id in available_tools.keys():
        if tool_id not in tool_priority:
            tool_priority.append(tool_id)
    
    return (None, tool_priority if tool_priority else list(available_tools.keys()))
