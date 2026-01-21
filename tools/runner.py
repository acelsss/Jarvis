"""Tool runner."""
from typing import Dict, Any, List

from core.contracts.tool import Tool
from core.contracts.tool_result import ToolResult


class ToolRunner:
    """工具执行器。"""
    
    async def run(self, tool: Tool, step_id: str, params: Dict[str, Any] = None) -> ToolResult:
        """运行工具并统一记录结果。
        
        Args:
            tool: 工具对象
            step_id: 步骤ID
            params: 执行参数
            
        Returns:
            工具执行结果
        """
        try:
            result = await tool.execute(params or {})
            
            # 提取 evidence_refs（如生成的文件路径）
            evidence_refs: List[str] = []
            if isinstance(result, dict):
                # 检查是否有文件路径
                if "path" in result:
                    evidence_refs.append(result["path"])
                if "evidence_refs" in result:
                    evidence_refs.extend(result.get("evidence_refs", []))
            
            return ToolResult(
                tool_id=tool.tool_id,
                step_id=step_id,
                success=True,
                result=result,
                evidence_refs=evidence_refs,
            )
        except Exception as e:
            return ToolResult(
                tool_id=tool.tool_id,
                step_id=step_id,
                success=False,
                error=str(e),
                evidence_refs=[],
            )

    def run_missing_mcp(self, tool_id: str, step_id: str) -> ToolResult:
        """占位：MCP client 未接入时的失败结果。"""
        return ToolResult(
            tool_id=tool_id,
            step_id=step_id,
            success=False,
            error="未接入 MCP client",
            evidence_refs=[],
        )
