"""Routing logic."""
import json
import os
from typing import Any, Dict, List, Optional, Tuple

from core.contracts.task import Task
from core.contracts.skill import JarvisSkill
from core.llm.schemas import ROUTE_SCHEMA


def _truncate_text(text: str, max_len: int = 120) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _summarize_skills(skills: Dict[str, JarvisSkill]) -> List[Dict[str, Any]]:
    summaries = []
    for skill_id, skill in skills.items():
        summaries.append(
            {
                "id": skill_id,
                "name": skill.name,
                "tags": skill.tags,
                "description": _truncate_text(skill.description or ""),
            }
        )
    return summaries


def _summarize_tools(tools: Dict[str, Any]) -> List[Dict[str, Any]]:
    summaries = []
    for tool_id, tool in tools.items():
        name = getattr(tool, "name", tool_id)
        description = getattr(tool, "description", "")
        tags = getattr(tool, "tags", [])
        summaries.append(
            {
                "id": tool_id,
                "name": name,
                "tags": tags,
                "description": _truncate_text(description or ""),
            }
        )
    return summaries


def _get_llm_model(provider: str) -> Optional[str]:
    provider = provider.strip().lower()
    if provider == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    return None


def _log_llm_route(
    audit_logger: Any,
    provider: str,
    purpose: str,
    confidence: Optional[float],
    reason: str,
    selected_skill_id: Optional[str],
    selected_tool_ids: List[str],
) -> None:
    if not audit_logger:
        return
    details = {
        "provider": provider,
        "model": _get_llm_model(provider),
        "purpose": purpose,
        "confidence": confidence,
        "reason": _truncate_text(reason or "", max_len=200),
        "selected_skill_id": selected_skill_id,
        "selected_tool_ids": selected_tool_ids,
    }
    audit_logger.log("llm.route", details)


def route_task(
    task: Task,
    available_tools: Dict[str, Any] = None,
    available_skills: Dict[str, JarvisSkill] = None,
    llm_client: Any = None,
    audit_logger: Any = None,
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
    
    if tool_priority:
        return (None, tool_priority)

    # 3. 规则不确定时尝试 LLM 路由（可选）
    if llm_client:
        provider = os.getenv("LLM_PROVIDER", "unknown")
        purpose = "route"
        try:
            skills_summary = _summarize_skills(available_skills)
            tools_summary = _summarize_tools(available_tools)
            system = "\n".join(
                [
                    "You are a routing assistant.",
                    "Choose ONE route: skill or tools.",
                    "Return JSON ONLY.",
                    "Available skills (summary JSON):",
                    json.dumps(skills_summary, ensure_ascii=False),
                    "Available tools (summary JSON):",
                    json.dumps(tools_summary, ensure_ascii=False),
                ]
            )
            user = "\n".join(
                [
                    f"Task description: {task.description}",
                    "Decide best route using available skills/tools only.",
                ]
            )
            llm_result = llm_client.complete_json(
                purpose=purpose,
                system=system,
                user=user,
                schema_hint=ROUTE_SCHEMA,
            )
            if isinstance(llm_result, dict):
                route_type = llm_result.get("route_type")
                skill_id = llm_result.get("skill_id")
                tool_ids = llm_result.get("tool_ids") or []
                reason = llm_result.get("reason", "")
                confidence = llm_result.get("confidence")

                selected_skill = None
                selected_tools: List[str] = []

                if route_type == "skill" and skill_id:
                    selected_skill = available_skills.get(skill_id)
                    if selected_skill:
                        _log_llm_route(
                            audit_logger,
                            provider,
                            purpose,
                            confidence if isinstance(confidence, (int, float)) else None,
                            reason,
                            skill_id,
                            [],
                        )
                        return (selected_skill, [])

                if isinstance(tool_ids, list):
                    selected_tools = [
                        tool_id
                        for tool_id in tool_ids
                        if tool_id in available_tools
                    ]

                _log_llm_route(
                    audit_logger,
                    provider,
                    purpose,
                    confidence if isinstance(confidence, (int, float)) else None,
                    reason,
                    None,
                    selected_tools,
                )
                if selected_tools:
                    return (None, selected_tools)
        except Exception:
            _log_llm_route(
                audit_logger,
                provider,
                purpose,
                None,
                "llm_error",
                None,
                [],
            )
            print("LLM 路由不可用，已回退规则路由。")

    return (None, list(available_tools.keys()))
