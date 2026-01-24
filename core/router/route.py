"""Routing logic."""
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from core.contracts.task import Task
from core.contracts.skill import JarvisSkill
from core.llm.schemas import ROUTE_SCHEMA, ROUTE_SCHEMA_V0_2, CAPABILITY_INDEX_SCHEMA_HINT
from core.prompts.loader import PromptLoader


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
    confidence: Optional[float],
    route_type: str,
    skill_id: Optional[str],
    tool_ids: List[str],
    questions: Optional[List[str]] = None,
) -> None:
    if not audit_logger:
        return
    safe_questions = []
    if isinstance(questions, list):
        safe_questions = [_truncate_text(q or "", max_len=120) for q in questions[:3]]
    details = {
        "provider": provider,
        "model": _get_llm_model(provider),
        "confidence": confidence,
        "route_type": route_type,
        "skill_id": skill_id,
        "tool_ids": tool_ids,
        "questions": safe_questions,
    }
    audit_logger.log("llm.route", details)


def _hard_guard_match(text: str) -> Optional[str]:
    lowered = text.lower()
    patterns = [
        r"\brm\b",
        r"\bsudo\b",
        r"\bdelete\b",
        r"\boverwrite\b",
        r"\bexecute script\b",
        r"\brun script\b",
        r"\bpayment\b",
        r"\bpay\b",
        r"\blogin\b",
        "删除",
        "覆盖",
        "执行脚本",
        "付款",
        "支付",
        "转账",
        "登录",
        "操作电脑",
        "点击",
        "输入",
    ]
    for pattern in patterns:
        if pattern.startswith(r"\b"):
            if re.search(pattern, lowered):
                return pattern
        elif pattern in lowered:
            return pattern
    return None


def _truncate_capability_index(capability_index: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(capability_index, dict):
        return {}
    skills = []
    for item in capability_index.get("skills", []) or []:
        if not isinstance(item, dict):
            continue
        skills.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "description": _truncate_text(item.get("description") or "", 120),
                "tags": item.get("tags") or [],
                "allowed_tools": item.get("allowed_tools") or [],
                "disable_model_invocation": bool(item.get("disable_model_invocation", False)),
                "path": item.get("path"),
            }
        )
    tools = []
    for item in capability_index.get("tools", []) or []:
        if not isinstance(item, dict):
            continue
        tools.append(
            {
                "id": item.get("id"),
                "description": _truncate_text(item.get("description") or "", 120),
                "risk_default": item.get("risk_default"),
            }
        )
    return {
        "skills": skills,
        "tools": tools,
        "mcp": capability_index.get("mcp", []) or [],
    }


def _build_context_summary(context_bundle: Any) -> Dict[str, Any]:
    if not isinstance(context_bundle, dict):
        return {}
    identity = context_bundle.get("identity") or {}
    preferences = identity.get("preferences") or {}
    return {
        "task_id": context_bundle.get("task_id"),
        "status": context_bundle.get("status"),
        "preferences": preferences.get("sandbox", {}) or {},
        "openmemory_count": len(context_bundle.get("openmemory", []) or []),
    }


def _normalize_confidence(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _validate_route_decision(
    decision: Dict[str, Any],
    capability_index: Dict[str, Any],
) -> Tuple[bool, str]:
    route_type = decision.get("route_type")
    if route_type not in {"qa", "skill", "tool", "mcp", "clarify"}:
        return False, "invalid_route_type"

    skill_ids = {item.get("id") for item in capability_index.get("skills", []) or []}
    tool_ids = {item.get("id") for item in capability_index.get("tools", []) or []}

    if route_type == "skill":
        skill_id = decision.get("skill_id")
        if not skill_id or skill_id not in skill_ids:
            return False, "invalid_skill_id"
    if route_type in {"tool", "mcp"}:
        selected_tools = decision.get("tool_ids")
        if not isinstance(selected_tools, list) or not selected_tools:
            return False, "invalid_tool_ids"
        if route_type == "tool":
            if any(tool_id not in tool_ids for tool_id in selected_tools):
                return False, "unknown_tool_id"
        else:
            for tool_id in selected_tools:
                if tool_id in tool_ids:
                    continue
                if isinstance(tool_id, str) and tool_id.startswith("mcp."):
                    continue
                return False, "unknown_mcp_tool_id"
    if route_type == "clarify":
        questions = decision.get("clarify_questions")
        if not isinstance(questions, list) or not questions:
            return False, "invalid_clarify_questions"
    return True, "ok"


def route_llm_first(
    task_text: str,
    context_bundle: Any,
    capability_index: Dict[str, Any],
    llm_client: Any,
    audit_logger: Any = None,
    chat_history_messages: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """LLM-first 路由，输出 RouteDecision 字典。"""
    guard_hit = _hard_guard_match(task_text)
    if guard_hit:
        tool_ids = [
            tool.get("id")
            for tool in capability_index.get("tools", []) or []
            if isinstance(tool, dict) and tool.get("id") == "shell"
        ]
        if not tool_ids:
            tool_ids = [
                tool.get("id")
                for tool in capability_index.get("tools", []) or []
                if isinstance(tool, dict) and tool.get("id")
            ]
        decision = {
            "route_type": "tool",
            "reason": f"hard_guard:{guard_hit}",
            "confidence": 1.0,
            "tool_ids": tool_ids,
            "min_risk": "R2",
        }
        _log_llm_route(
            audit_logger,
            provider="hard_guard",
            confidence=1.0,
            route_type="tool",
            skill_id=None,
            tool_ids=tool_ids,
            questions=None,
        )
        return decision

    if not llm_client:
        return {"fallback_to_rule": True, "reason": "llm_unavailable"}

    provider = os.getenv("LLM_PROVIDER", "unknown")
    truncated_index = _truncate_capability_index(capability_index or {})
    context_summary = _build_context_summary(context_bundle)
    
    loader = PromptLoader()
    parsed = loader.parse("router/llm_first.md")
    
    system_prompt = loader.render(
        parsed["sections"]["system"],
        {
            "route_schema": ROUTE_SCHEMA_V0_2,
            "capability_index_schema": CAPABILITY_INDEX_SCHEMA_HINT,
            "capability_index_json": json.dumps(truncated_index, ensure_ascii=False),
        },
        strict=True,
    )
    user_prompt = loader.render(
        parsed["sections"].get("user", ""),
        {
            "task_text": task_text,
            "context_summary_json": json.dumps(context_summary, ensure_ascii=False),
        },
        strict=True,
    )
    try:
        llm_result = llm_client.complete_json(
            purpose="route",
            system=system_prompt,
            user=user_prompt,
            schema_hint=ROUTE_SCHEMA_V0_2,
            chat_history_messages=chat_history_messages,
        )
    except Exception:
        return {"fallback_to_rule": True, "reason": "llm_error"}

    if not isinstance(llm_result, dict):
        return {"fallback_to_rule": True, "reason": "invalid_llm_result"}

    confidence = _normalize_confidence(llm_result.get("confidence"))
    if confidence is not None and confidence < 0.45:
        decision = {
            "route_type": "clarify",
            "reason": "low_confidence",
            "confidence": confidence,
            "clarify_questions": llm_result.get("clarify_questions")
            or ["请补充目标与约束，方便选择合适的执行路径。"],
        }
        _log_llm_route(
            audit_logger,
            provider=provider,
            confidence=confidence,
            route_type="clarify",
            skill_id=None,
            tool_ids=[],
            questions=decision.get("clarify_questions"),
        )
        return decision

    is_valid, reason = _validate_route_decision(llm_result, truncated_index)
    if not is_valid:
        return {"fallback_to_rule": True, "reason": reason}

    decision = {
        "route_type": llm_result.get("route_type"),
        "reason": llm_result.get("reason") or "",
        "confidence": confidence,
        "skill_id": llm_result.get("skill_id"),
        "tool_ids": llm_result.get("tool_ids") or [],
        "clarify_questions": llm_result.get("clarify_questions") or [],
    }
    _log_llm_route(
        audit_logger,
        provider=provider,
        confidence=confidence,
        route_type=decision["route_type"],
        skill_id=decision.get("skill_id"),
        tool_ids=decision.get("tool_ids") or [],
        questions=decision.get("clarify_questions"),
    )
    return decision


def route_task(
    task: Task,
    available_tools: Dict[str, Any] = None,
    available_skills: Dict[str, JarvisSkill] = None,
    llm_client: Any = None,
    audit_logger: Any = None,
    chat_history_messages: Optional[List[Dict[str, str]]] = None,
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
            
            loader = PromptLoader()
            parsed = loader.parse("router/rule_fallback.md")
            
            system_prompt = loader.render(
                parsed["sections"]["system"],
                {
                    "skills_summary_json": json.dumps(skills_summary, ensure_ascii=False),
                    "tools_summary_json": json.dumps(tools_summary, ensure_ascii=False),
                },
                strict=True,
            )
            user_prompt = loader.render(
                parsed["sections"].get("user", ""),
                {
                    "task_description": task.description,
                },
                strict=True,
            )
            llm_result = llm_client.complete_json(
                purpose=purpose,
                system=system_prompt,
                user=user_prompt,
                schema_hint=ROUTE_SCHEMA,
                chat_history_messages=chat_history_messages,
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
                            confidence if isinstance(confidence, (int, float)) else None,
                            "skill",
                            skill_id,
                            [],
                            None,
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
                    confidence if isinstance(confidence, (int, float)) else None,
                    "tool",
                    None,
                    selected_tools,
                    None,
                )
                if selected_tools:
                    return (None, selected_tools)
        except Exception:
            _log_llm_route(
                audit_logger,
                provider,
                None,
                "error",
                None,
                [],
                None,
            )
            print("LLM 路由不可用，已回退规则路由。")

    return (None, list(available_tools.keys()))
