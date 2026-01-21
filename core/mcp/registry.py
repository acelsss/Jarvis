"""MCP registry placeholder."""
from typing import List, Dict, Any


class McpRegistry:
    """占位 MCP 注册表。"""

    def list_mcp_tools_summary(self) -> List[Dict[str, Any]]:
        """返回 MCP 工具摘要列表（暂为空）。"""
        return []

    def tool_exists(self, tool_id: str) -> bool:
        """检查 MCP 工具是否存在（占位，恒为 False）。"""
        _ = tool_id
        return False
