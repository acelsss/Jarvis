"""OpenMemory adapter interface and stub implementation."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

from core.contracts.tool import Tool
from core.contracts.memory import Memory


class OpenMemoryAdapter(ABC):
    """OpenMemory 适配器接口。
    
    定义与 OpenMemory 系统交互的标准接口，支持搜索和存储操作。
    """
    
    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Memory]:
        """搜索记忆。
        
        Args:
            query: 搜索查询字符串
            top_k: 返回结果数量
            filters: 可选的过滤条件
            
        Returns:
            匹配的记忆列表
        """
        pass
    
    @abstractmethod
    async def upsert(
        self,
        memory: Memory,
        namespace: Optional[str] = None,
    ) -> str:
        """插入或更新记忆。
        
        Args:
            memory: 记忆对象
            namespace: 可选的命名空间
            
        Returns:
            记忆ID
        """
        pass
    
    @abstractmethod
    async def get(
        self,
        memory_id: str,
        namespace: Optional[str] = None,
    ) -> Optional[Memory]:
        """根据ID获取记忆。
        
        Args:
            memory_id: 记忆ID
            namespace: 可选的命名空间
            
        Returns:
            记忆对象，如果不存在则返回None
        """
        pass


class OpenMemoryStubAdapter(OpenMemoryAdapter):
    """OpenMemory 适配器 stub 实现。
    
    v0.1 提供固定返回空或简单命中的实现，用于测试和开发。
    """
    
    def __init__(self):
        """初始化 stub 适配器。"""
        self._stub_memories: Dict[str, Memory] = {}
    
    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Memory]:
        """搜索记忆（stub实现）。
        
        v0.1: 如果查询包含特定关键词，返回一个简单的命中结果。
        """
        # TODO: 实现真实的 OpenMemory 搜索
        # v0.1: 简单 stub - 如果查询包含 "test" 或 "示例"，返回一个固定结果
        results = []
        if "test" in query.lower() or "示例" in query.lower():
            from core.utils.ids import generate_id
            from datetime import datetime
            stub_memory = Memory(
                memory_id=generate_id("memory"),
                content=f"Stub memory for query: {query}",
                metadata={"source": "stub", "query": query},
                tags=["stub"],
                created_at=datetime.now(),
            )
            results.append(stub_memory)
        
        return results[:top_k]
    
    async def upsert(
        self,
        memory: Memory,
        namespace: Optional[str] = None,
    ) -> str:
        """插入或更新记忆（stub实现）。
        
        v0.1: 简单存储在内存字典中。
        """
        # TODO: 实现真实的 OpenMemory 存储
        # v0.1: 简单 stub - 存储在内存字典中
        key = f"{namespace}:{memory.memory_id}" if namespace else memory.memory_id
        self._stub_memories[key] = memory
        return memory.memory_id
    
    async def get(
        self,
        memory_id: str,
        namespace: Optional[str] = None,
    ) -> Optional[Memory]:
        """根据ID获取记忆（stub实现）。
        
        v0.1: 从内存字典中查找。
        """
        # TODO: 实现真实的 OpenMemory 检索
        # v0.1: 简单 stub - 从内存字典中查找
        key = f"{namespace}:{memory_id}" if namespace else memory_id
        return self._stub_memories.get(key)


class OpenMemoryStub(Tool):
    """OpenMemory 工具包装（兼容旧接口）。
    
    将 OpenMemoryAdapter 包装为 Tool 接口，用于工具注册表。
    """
    
    def __init__(self, adapter: Optional[OpenMemoryAdapter] = None):
        """初始化 OpenMemory 工具。
        
        Args:
            adapter: OpenMemory 适配器实例，如果为None则使用 stub 实现
        """
        self.adapter = adapter or OpenMemoryStubAdapter()
        
        super().__init__(
            tool_id="openmemory",
            name="OpenMemory Integration",
            description="OpenMemory 记忆系统集成",
            parameters={
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["search", "upsert", "get"]},
                    "query": {"type": "string", "description": "搜索查询（search操作需要）"},
                    "memory_id": {"type": "string", "description": "记忆ID（get操作需要）"},
                    "content": {"type": "string", "description": "记忆内容（upsert操作需要）"},
                    "namespace": {"type": "string", "description": "命名空间（可选）"},
                },
                "required": ["operation"],
            },
            risk_level="low",
            requires_approval=False,
        )
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行 OpenMemory 操作。"""
        operation = params.get("operation")
        namespace = params.get("namespace")
        
        if operation == "search":
            query = params.get("query", "")
            top_k = params.get("top_k", 10)
            memories = await self.adapter.search(query, top_k=top_k)
            return {
                "success": True,
                "results": [m.to_dict() for m in memories],
                "count": len(memories),
            }
        
        elif operation == "upsert":
            from core.utils.ids import generate_id
            from datetime import datetime
            content = params.get("content", "")
            memory = Memory(
                memory_id=generate_id("memory"),
                content=content,
                metadata=params.get("metadata", {}),
                tags=params.get("tags", []),
                created_at=datetime.now(),
            )
            memory_id = await self.adapter.upsert(memory, namespace=namespace)
            return {
                "success": True,
                "memory_id": memory_id,
                "message": "Memory upserted",
            }
        
        elif operation == "get":
            memory_id = params.get("memory_id")
            if not memory_id:
                raise ValueError("memory_id is required for get operation")
            memory = await self.adapter.get(memory_id, namespace=namespace)
            if memory:
                return {
                    "success": True,
                    "memory": memory.to_dict(),
                }
            else:
                return {
                    "success": False,
                    "message": "Memory not found",
                }
        
        else:
            raise ValueError(f"Unknown operation: {operation}")
