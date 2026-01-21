"""Tool registry."""
from typing import Dict, Optional, List
import re

from core.contracts.tool import Tool


class ToolRegistry:
    """工具注册表。
    
    支持本地工具和外部工具组（通过 namespace）的统一注册和管理。
    """
    
    def __init__(self):
        """初始化工具注册表。"""
        self.tools: Dict[str, Tool] = {}  # tool_id -> Tool
        self.namespace_tools: Dict[str, Dict[str, Tool]] = {}  # namespace -> {tool_name -> Tool}
    
    def register(self, tool: Tool, namespace: Optional[str] = None) -> None:
        """注册工具。
        
        Args:
            tool: 工具对象
            namespace: 可选的命名空间（如 "mcp:server1"），如果提供则注册为外部工具组
        """
        if namespace:
            # 注册到命名空间
            if namespace not in self.namespace_tools:
                self.namespace_tools[namespace] = {}
            
            # 使用 tool_id 作为工具名称（或从 tool_id 提取）
            tool_name = tool.tool_id
            self.namespace_tools[namespace][tool_name] = tool
            
            # 同时注册完整ID（namespace:tool_name）到主注册表，便于查找
            full_id = f"{namespace}:{tool_name}"
            self.tools[full_id] = tool
        else:
            # 注册为本地工具
            self.tools[tool.tool_id] = tool
    
    def register_namespace_tools(
        self,
        namespace: str,
        tools: Dict[str, Tool],
    ) -> None:
        """批量注册命名空间工具组。
        
        Args:
            namespace: 命名空间（如 "mcp:server1"）
            tools: 工具字典 {tool_name -> Tool}
        """
        if namespace not in self.namespace_tools:
            self.namespace_tools[namespace] = {}
        
        for tool_name, tool in tools.items():
            self.namespace_tools[namespace][tool_name] = tool
            # 注册完整ID
            full_id = f"{namespace}:{tool_name}"
            self.tools[full_id] = tool
    
    def get(self, tool_id: str) -> Optional[Tool]:
        """获取工具。
        
        支持以下格式：
        - 本地工具ID: "file"
        - 命名空间工具ID: "mcp:server1:tool_name"
        
        Args:
            tool_id: 工具ID（支持命名空间格式）
            
        Returns:
            工具对象，如果不存在则返回None
        """
        # 直接查找
        if tool_id in self.tools:
            return self.tools[tool_id]
        
        # 尝试解析命名空间格式
        # 格式: namespace:tool_name 或 namespace:server:tool_name
        parts = tool_id.split(":", 2)
        if len(parts) >= 2:
            namespace = parts[0]
            tool_name = parts[-1]  # 取最后一部分作为工具名
            
            if namespace in self.namespace_tools:
                return self.namespace_tools[namespace].get(tool_name)
        
        return None
    
    def list_all(self, include_namespace: bool = True) -> Dict[str, Tool]:
        """列出所有工具。
        
        Args:
            include_namespace: 是否包含命名空间工具
            
        Returns:
            工具字典 {tool_id -> Tool}
        """
        if include_namespace:
            return self.tools.copy()
        else:
            # 只返回本地工具（不包含命名空间工具）
            return {
                tool_id: tool
                for tool_id, tool in self.tools.items()
                if ":" not in tool_id
            }
    
    def list_namespace(self, namespace: str) -> Dict[str, Tool]:
        """列出指定命名空间的所有工具。
        
        Args:
            namespace: 命名空间
            
        Returns:
            工具字典 {tool_name -> Tool}
        """
        return self.namespace_tools.get(namespace, {}).copy()
    
    def list_namespaces(self) -> List[str]:
        """列出所有已注册的命名空间。
        
        Returns:
            命名空间列表
        """
        return list(self.namespace_tools.keys())
    
    def unregister(self, tool_id: str) -> bool:
        """取消注册工具。
        
        Args:
            tool_id: 工具ID
            
        Returns:
            是否成功取消注册
        """
        if tool_id in self.tools:
            tool = self.tools.pop(tool_id)
            
            # 如果是命名空间工具，也从命名空间字典中移除
            parts = tool_id.split(":", 2)
            if len(parts) >= 2:
                namespace = parts[0]
                tool_name = parts[-1]
                if namespace in self.namespace_tools:
                    self.namespace_tools[namespace].pop(tool_name, None)
            
            return True
        return False
