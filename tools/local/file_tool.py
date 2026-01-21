"""File tool implementation."""
import os
from pathlib import Path
from typing import Dict, Any

from core.contracts.tool import Tool
from core.contracts.risk import RISK_LEVEL_R1
from core.platform.config import Config


class FileTool(Tool):
    """文件操作工具。"""
    
    def __init__(self, sandbox_root: str = None):
        """初始化文件工具。
        
        Args:
            sandbox_root: 沙箱根目录（如果为None则从配置读取）
        """
        if sandbox_root is None:
            config = Config()
            preferences = config.load_yaml("preferences.yaml")
            sandbox_root = preferences.get("sandbox", {}).get("sandbox_root", "./sandbox")
            # 也支持从环境变量读取
            sandbox_root = os.getenv("SANDBOX_ROOT", sandbox_root)
        
        self.sandbox_root = Path(sandbox_root).resolve()
        # 确保沙箱目录存在
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        
        super().__init__(
            tool_id="file",
            name="File Operations",
            description="文件读写操作",
            parameters={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["read", "write", "list"]},
                    "path": {"type": "string", "description": "文件路径（相对于sandbox_root）"},
                    "content": {"type": "string", "description": "写入内容（write操作需要）"},
                },
                "required": ["operation", "path"],
            },
            risk_level=RISK_LEVEL_R1,
            requires_approval=False,
        )
    
    def _resolve_path(self, path_str: str) -> Path:
        """解析路径，确保在 sandbox_root 内。
        
        Args:
            path_str: 相对路径字符串
            
        Returns:
            解析后的绝对路径
        """
        # 移除前导斜杠和点
        path_str = path_str.lstrip("/.")
        # 构建完整路径
        full_path = (self.sandbox_root / path_str).resolve()
        
        # 安全检查：确保路径在 sandbox_root 内
        try:
            full_path.relative_to(self.sandbox_root)
        except ValueError:
            raise ValueError(f"路径 {path_str} 超出沙箱范围: {self.sandbox_root}")
        
        return full_path
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行文件操作（强制在 sandbox_root 内）。"""
        operation = params.get("operation")
        path_str = params.get("path")
        
        if not operation or not path_str:
            raise ValueError("operation and path are required")
        
        path = self._resolve_path(path_str)
        
        if operation == "read":
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path_str}")
            content = path.read_text(encoding="utf-8")
            return {"content": content, "path": str(path)}
        
        elif operation == "write":
            content = params.get("content", "")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return {
                "success": True,
                "path": str(path),
                "evidence_refs": [str(path)],  # 作为证据引用
            }
        
        elif operation == "list":
            if not path.exists():
                raise FileNotFoundError(f"Path not found: {path_str}")
            if path.is_file():
                return {"type": "file", "path": str(path)}
            files = [str(p) for p in path.iterdir()]
            return {"type": "directory", "files": files, "path": str(path)}
        
        else:
            raise ValueError(f"Unknown operation: {operation}")
