# Jarvis 扩展点说明 v0.1

本文档说明 Jarvis v0.1 中定义的扩展接口和集成挂点，供未来实现真实集成时参考。

## 概述

v0.1 版本定义了以下扩展接口，但仅提供 stub 实现：
- OpenMemory 适配器接口
- MCP 客户端接口
- Desktop Operator（预留）

所有接口都遵循以下原则：
- 使用 ABC 抽象基类定义接口
- 提供 stub 实现用于开发和测试
- 不引入新依赖
- 接口设计考虑未来真实实现的扩展性

## OpenMemory 集成

### 接口定义

**文件**: `tools/local/openmemory_stub.py`

**接口**: `OpenMemoryAdapter` (ABC)

```python
class OpenMemoryAdapter(ABC):
    @abstractmethod
    async def search(query: str, top_k: int = 10, filters: Optional[Dict] = None) -> List[Memory]:
        """搜索记忆"""
        pass
    
    @abstractmethod
    async def upsert(memory: Memory, namespace: Optional[str] = None) -> str:
        """插入或更新记忆"""
        pass
    
    @abstractmethod
    async def get(memory_id: str, namespace: Optional[str] = None) -> Optional[Memory]:
        """根据ID获取记忆"""
        pass
```

### Stub 实现

**类**: `OpenMemoryStubAdapter`

- `search()`: 如果查询包含 "test" 或 "示例"，返回一个固定结果
- `upsert()`: 存储在内存字典中
- `get()`: 从内存字典中查找

### 使用方式

```python
from tools.local.openmemory_stub import OpenMemoryAdapter, OpenMemoryStubAdapter

# v0.1: 使用 stub
adapter = OpenMemoryStubAdapter()

# 未来: 替换为真实实现
# from tools.local.openmemory_real import OpenMemoryRealAdapter
# adapter = OpenMemoryRealAdapter(api_key="...", endpoint="...")
```

### 集成点

1. **Context Engine** (`core/context_engine/build_context.py`)
   - 构建上下文时调用 `adapter.search()` 获取相关记忆

2. **Memory 存储** (未来)
   - 任务执行后调用 `adapter.upsert()` 存储结果

3. **Tool 包装** (`OpenMemoryStub`)
   - 将适配器包装为 Tool 接口，可通过工具注册表使用

## MCP (Model Context Protocol) 集成

### 接口定义

**文件**: `tools/mcp/mcp_client.py`

**接口**: `MCPClient` (ABC)

```python
class MCPClient(ABC):
    @abstractmethod
    async def connect(server_url: str, config: Optional[Dict] = None) -> bool:
        """连接到 MCP 服务器"""
        pass
    
    @abstractmethod
    async def disconnect() -> None:
        """断开连接"""
        pass
    
    @abstractmethod
    async def list_tools() -> List[MCPTool]:
        """列出服务器提供的工具"""
        pass
    
    @abstractmethod
    async def call_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """调用 MCP 工具"""
        pass
    
    @abstractmethod
    def is_connected() -> bool:
        """检查连接状态"""
        pass
```

### Stub 实现

**类**: `MCPClientStub`

- `connect()`: 仅标记为已连接，不进行真实网络连接
- `disconnect()`: 仅标记为未连接
- `list_tools()`: 返回一个预定义的 stub 工具
- `call_tool()`: 返回固定的 stub 结果

### 使用方式

```python
from tools.mcp.mcp_client import MCPClient, MCPClientStub

# v0.1: 使用 stub
client = MCPClientStub()
await client.connect("http://mcp-server:8000")
tools = await client.list_tools()

# 未来: 替换为真实实现
# from tools.mcp.mcp_real import MCPRealClient
# client = MCPRealClient()
# await client.connect("http://mcp-server:8000")
```

### 工具注册

通过命名空间注册 MCP 工具：

```python
from tools.registry import ToolRegistry
from tools.mcp.mcp_client import MCPClientStub

registry = ToolRegistry()
client = MCPClientStub()
await client.connect("http://mcp-server:8000")
mcp_tools = await client.list_tools()

# 将 MCP 工具注册到命名空间
mcp_tool_dict = {
    tool.name: MCPToolWrapper(tool, client) 
    for tool in mcp_tools
}
registry.register_namespace_tools(
    namespace="mcp:server1",
    tools=mcp_tool_dict
)

# 使用工具
tool = registry.get("mcp:server1:tool_name")
```

### 集成点

1. **工具注册表** (`tools/registry.py`)
   - 支持通过命名空间注册外部工具组
   - 工具ID格式: `mcp:<server>:<tool_name>`

2. **Router** (未来)
   - 路由时考虑 MCP 工具

3. **ToolRunner** (未来)
   - 执行 MCP 工具时调用 `client.call_tool()`

## Desktop Operator（预留）

### 预留位置

**文件**: `tools/desktop/operator.py` (v0.1 未创建)

### 预期接口

```python
class DesktopOperator(ABC):
    @abstractmethod
    async def click(x: int, y: int) -> bool:
        """点击屏幕坐标"""
        pass
    
    @abstractmethod
    async def type_text(text: str) -> bool:
        """输入文本"""
        pass
    
    @abstractmethod
    async def get_window_list() -> List[Window]:
        """获取窗口列表"""
        pass
```

### 实现状态

- v0.1: 仅预留接口定义位置
- 未来: 实现桌面自动化能力

## 工具注册表扩展

### 命名空间支持

**文件**: `tools/registry.py`

**功能**:
- 支持本地工具直接注册
- 支持外部工具组通过命名空间注册
- 统一的工具查找接口

**API**:

```python
# 注册本地工具
registry.register(file_tool)

# 注册命名空间工具
registry.register(tool, namespace="mcp:server1")

# 批量注册命名空间工具
registry.register_namespace_tools(
    namespace="mcp:server1",
    tools={"tool1": tool1, "tool2": tool2}
)

# 获取工具（支持命名空间格式）
tool = registry.get("mcp:server1:tool_name")

# 列出命名空间工具
tools = registry.list_namespace("mcp:server1")

# 列出所有命名空间
namespaces = registry.list_namespaces()
```

### 工具ID格式

- **本地工具**: `tool_id` (如 `"file"`, `"shell"`)
- **命名空间工具**: `namespace:tool_name` (如 `"mcp:server1:remote_tool"`)

## 实现指南

### 实现真实 OpenMemory 适配器

1. 继承 `OpenMemoryAdapter`
2. 实现所有抽象方法
3. 处理 API 认证和错误
4. 实现连接池和重试逻辑

```python
class OpenMemoryRealAdapter(OpenMemoryAdapter):
    def __init__(self, api_key: str, endpoint: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.client = OpenMemoryClient(api_key, endpoint)
    
    async def search(self, query: str, top_k: int = 10, filters: Optional[Dict] = None):
        return await self.client.search(query, top_k, filters)
    
    # ... 实现其他方法
```

### 实现真实 MCP 客户端

1. 继承 `MCPClient`
2. 实现 MCP 协议通信
3. 处理连接管理和错误重试
4. 实现工具调用和结果解析

```python
class MCPRealClient(MCPClient):
    def __init__(self):
        self.websocket = None
        self._connected = False
    
    async def connect(self, server_url: str, config: Optional[Dict] = None):
        # 实现 WebSocket 连接
        self.websocket = await connect_websocket(server_url)
        self._connected = True
        return True
    
    # ... 实现其他方法
```

## 约束说明

v0.1 版本的约束：

1. **不引入新依赖** - 所有接口定义不依赖外部库
2. **仅接口和占位** - 不实现真实集成逻辑
3. **向后兼容** - 接口设计考虑未来扩展
4. **统一注册** - 所有工具通过统一注册表管理

## 测试

所有接口都提供 stub 实现，可用于：
- 单元测试
- 集成测试
- 开发环境验证

```python
# 测试示例
async def test_openmemory():
    adapter = OpenMemoryStubAdapter()
    results = await adapter.search("test")
    assert len(results) > 0

async def test_mcp():
    client = MCPClientStub()
    await client.connect("http://test:8000")
    tools = await client.list_tools()
    assert len(tools) > 0
```
