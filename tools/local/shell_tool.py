"""Shell tool implementation."""
import asyncio
from typing import Dict, Any

from core.contracts.tool import Tool
from core.contracts.risk import RISK_LEVEL_R2


class ShellTool(Tool):
    """Shell 命令执行工具（v0.1 仅允许 echo）。"""
    
    # v0.1 允许的命令白名单
    ALLOWED_COMMANDS = ["echo"]
    
    def __init__(self):
        """初始化 Shell 工具。"""
        super().__init__(
            tool_id="shell",
            name="Shell Command",
            description="执行 shell 命令（v0.1 仅允许 echo）",
            parameters={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令（仅允许 echo）"},
                },
                "required": ["command"],
            },
            risk_level=RISK_LEVEL_R2,  # R2 风险等级，需要审批
            requires_approval=True,
        )
    
    def _is_allowed(self, command: str) -> bool:
        """检查命令是否允许执行。
        
        Args:
            command: 命令字符串
            
        Returns:
            是否允许
        """
        command_lower = command.strip().lower()
        # 检查是否以允许的命令开头
        for allowed in self.ALLOWED_COMMANDS:
            if command_lower.startswith(allowed):
                return True
        return False
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行 shell 命令（v0.1 仅允许 echo）。"""
        command = params.get("command", "")
        if not command:
            raise ValueError("command parameter is required")
        
        # v0.1: 安全检查，仅允许 echo
        if not self._is_allowed(command):
            raise ValueError(
                f"v0.1 版本禁止执行此命令: {command}。"
                f"仅允许的命令: {', '.join(self.ALLOWED_COMMANDS)}"
            )
        
        # 执行命令
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        return {
            "exit_code": process.returncode,
            "stdout": stdout.decode("utf-8"),
            "stderr": stderr.decode("utf-8"),
            "command": command,
        }
