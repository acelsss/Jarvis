"""Capability index builder for routing."""
from typing import Any, Dict, List, Optional


def _build_mcp_summary(mcp_registry: Any) -> List[Dict[str, Any]]:
    if not mcp_registry:
        return []

    if hasattr(mcp_registry, "list_mcp_summary"):
        return list(mcp_registry.list_mcp_summary())

    if isinstance(mcp_registry, list):
        return mcp_registry

    if isinstance(mcp_registry, dict):
        return mcp_registry.get("mcp", []) or mcp_registry.get("servers", []) or []

    return []


def build_capability_index(
    skills_registry: Any,
    tools_registry: Any,
    mcp_registry: Optional[Any] = None,
) -> Dict[str, Any]:
    """构建 capability index（仅技能/工具摘要）。"""
    skills = []
    if skills_registry and hasattr(skills_registry, "list_skill_metadata"):
        skills = list(skills_registry.list_skill_metadata())

    tools = []
    if tools_registry and hasattr(tools_registry, "list_tools_summary"):
        tools = list(tools_registry.list_tools_summary())

    return {
        "skills": skills,
        "tools": tools,
        "mcp": _build_mcp_summary(mcp_registry),
    }
