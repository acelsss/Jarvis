"""MCP client abstract interface and stub implementation."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class MCPTool:
    """MCP 工具定义。"""
    
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
    ):
        """初始化 MCP 工具定义。
        
        Args:
            name: 工具名称
            description: 工具描述
            input_schema: 输入参数 schema（JSON Schema）
        """
        self.name = name
        self.description = description
        self.input_schema = input_schema


class MCPClient(ABC):
    """MCP 客户端抽象接口。
    
    定义与 MCP (Model Context Protocol) 服务器交互的标准接口。
    """
    
    @abstractmethod
    async def connect(self, server_url: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """连接到 MCP 服务器。
        
        Args:
            server_url: 服务器 URL
            config: 可选的连接配置
            
        Returns:
            连接是否成功
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """断开与 MCP 服务器的连接。"""
        pass
    
    @abstractmethod
    async def list_tools(self) -> List[MCPTool]:
        """列出服务器提供的所有工具。
        
        Returns:
            工具列表
        """
        pass
    
    @abstractmethod
    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """调用 MCP 工具。
        
        Args:
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            工具执行结果
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """检查是否已连接。
        
        Returns:
            是否已连接
        """
        pass


class MCPClientStub(MCPClient):
    """MCP 客户端 stub 实现。
    
    v0.1 提供占位实现，不进行真实的网络连接。
    """
    
    def __init__(self, server_url: Optional[str] = None):
        """初始化 MCP 客户端 stub。
        
        Args:
            server_url: 服务器 URL（v0.1 不实际使用）
        """
        self.server_url = server_url
        self._connected = False
        self._stub_tools: List[MCPTool] = []
    
    async def connect(self, server_url: str, config: Optional[Dict[str, Any]] = None) -> bool:
        """连接到 MCP 服务器（stub实现）。
        
        v0.1: 仅标记为已连接，不进行真实连接。
        """
        # TODO: 实现真实的 MCP 服务器连接
        # v0.1: stub - 仅标记状态
        self.server_url = server_url
        self._connected = True
        print(f"[Stub] MCP client connected to {server_url}")
        return True
    
    async def disconnect(self) -> None:
        """断开连接（stub实现）。"""
        # TODO: 实现真实的断开连接逻辑
        # v0.1: stub - 仅标记状态
        self._connected = False
        print("[Stub] MCP client disconnected")
    
    async def list_tools(self) -> List[MCPTool]:
        """列出工具（stub实现）。
        
        v0.1: 返回空的工具列表或预定义的 stub 工具。
        """
        # TODO: 实现真实的工具列表获取
        # v0.1: stub - 返回空列表或预定义工具
        if not self._stub_tools:
            # 可以添加一些示例工具用于测试
            self._stub_tools = [
                MCPTool(
                    name="stub_tool",
                    description="Stub tool for testing",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "message": {"type": "string"},
                        },
                    },
                ),
            ]
        return self._stub_tools
    
    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """调用工具（stub实现）。
        
        v0.1: 返回固定的 stub 结果。
        """
        # TODO: 实现真实的 MCP 工具调用
        # v0.1: stub - 返回固定结果
        if not self._connected:
            raise RuntimeError("MCP client not connected")
        
        return {
            "success": True,
            "result": f"Stub result for tool '{tool_name}' with params: {params}",
            "message": "This is a stub implementation",
        }
    
    def is_connected(self) -> bool:
        """检查连接状态。"""
        return self._connected
