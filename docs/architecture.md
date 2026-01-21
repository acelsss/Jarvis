# Jarvis 架构文档 v0.1

## 核心设计原则

1. **契约驱动**: 所有交互通过明确定义的契约进行
2. **模块化**: 核心引擎、工具、技能解耦
3. **可审计**: 所有操作记录审计日志
4. **风险可控**: 关键操作需审批门控
5. **可扩展**: 通过接口和适配器支持外部系统集成

## 系统架构

```
┌─────────────┐
│   CLI App   │
└──────┬──────┘
       │
┌──────▼──────────────────┐
│   Orchestrator          │
│  - TaskManager          │
│  - Planner              │
│  - ApprovalGate        │
│  - Executor             │
└──────┬──────────────────┘
       │
┌──────▼──────────────────┐
│   Context Engine        │
│  - BuildContext         │
│  - ContextBundle        │
│  - OpenMemoryAdapter    │
└──────┬──────────────────┘
       │
┌──────▼──────────────────┐
│   Router                │
│  - Route                │
└──────┬──────────────────┘
       │
┌──────▼──────────────────┐
│   Tools / Skills        │
│  - Registry             │
│  - Runners              │
│  - MCPClient            │
└─────────────────────────┘
```

## 数据流

1. CLI 接收用户输入
2. Orchestrator 创建任务
3. Context Engine 构建上下文（可选：OpenMemory 搜索）
4. Router 路由到合适的工具/技能
5. Executor 执行并记录审计日志
6. Memory 存储任务结果

## v0.1 范围

- 基础契约定义（Task, Tool, Memory, Risk）
- 最小化 Orchestrator 实现
- CLI 入口
- 本地工具支持（shell, file）
- 基础审计日志
- Skills 子系统
- 扩展接口定义（OpenMemory, MCP, Desktop Operator）

## 扩展点说明

### OpenMemory 集成挂点

**位置**: `tools/local/openmemory_stub.py`

**接口**: `OpenMemoryAdapter` (ABC)

**方法**:
- `search(query, top_k, filters)` - 搜索记忆
- `upsert(memory, namespace)` - 插入或更新记忆
- `get(memory_id, namespace)` - 根据ID获取记忆

**实现状态**:
- v0.1: 提供 `OpenMemoryStubAdapter` stub 实现
- 未来: 实现真实的 OpenMemory API 客户端

**使用场景**:
- Context Engine 构建上下文时搜索相关记忆
- 任务执行后存储结果到 OpenMemory
- 跨任务记忆检索和复用

**集成方式**:
```python
from tools.local.openmemory_stub import OpenMemoryAdapter, OpenMemoryStubAdapter

# 使用 stub（v0.1）
adapter = OpenMemoryStubAdapter()

# 未来替换为真实实现
# adapter = OpenMemoryRealAdapter(api_key="...")
```

### MCP (Model Context Protocol) 集成挂点

**位置**: `tools/mcp/mcp_client.py`

**接口**: `MCPClient` (ABC)

**方法**:
- `connect(server_url, config)` - 连接到 MCP 服务器
- `disconnect()` - 断开连接
- `list_tools()` - 列出服务器提供的工具
- `call_tool(tool_name, params)` - 调用远程工具
- `is_connected()` - 检查连接状态

**实现状态**:
- v0.1: 提供 `MCPClientStub` stub 实现
- 未来: 实现真实的 MCP 协议客户端

**使用场景**:
- 连接外部 MCP 服务器获取工具
- 通过命名空间注册 MCP 工具（如 `mcp:server1:tool_name`）
- 执行远程工具调用

**集成方式**:
```python
from tools.mcp.mcp_client import MCPClient, MCPClientStub

# 使用 stub（v0.1）
client = MCPClientStub()

# 未来替换为真实实现
# client = MCPRealClient()
# await client.connect("http://mcp-server:8000")
# tools = await client.list_tools()
```

**工具注册**:
```python
# 通过命名空间注册 MCP 工具
registry.register_namespace_tools(
    namespace="mcp:server1",
    tools={tool.name: tool for tool in mcp_tools}
)
```

### Desktop Operator 集成挂点

**位置**: `tools/desktop/` (预留，v0.1 未实现)

**接口**: `DesktopOperator` (预留)

**预期功能**:
- 桌面应用操作（窗口管理、UI 交互）
- 系统级操作（文件系统、剪贴板等）
- 跨平台抽象（Windows/macOS/Linux）

**实现状态**:
- v0.1: 仅预留接口定义位置
- 未来: 实现桌面自动化能力

**使用场景**:
- 自动化桌面应用操作
- 系统级任务执行
- GUI 应用集成

**集成方式** (未来):
```python
from tools.desktop.operator import DesktopOperator

operator = DesktopOperator()
await operator.click(x, y)
await operator.type_text("Hello")
```

## 工具注册表扩展

**位置**: `tools/registry.py`

**命名空间支持**:
- 本地工具: 直接注册，如 `"file"`, `"shell"`
- 外部工具组: 通过命名空间注册，如 `"mcp:server1:tool_name"`

**API**:
- `register(tool, namespace=None)` - 注册工具（支持命名空间）
- `register_namespace_tools(namespace, tools)` - 批量注册命名空间工具
- `get(tool_id)` - 获取工具（支持命名空间格式）
- `list_namespace(namespace)` - 列出指定命名空间的工具
- `list_namespaces()` - 列出所有命名空间

**示例**:
```python
# 注册本地工具
registry.register(file_tool)

# 注册 MCP 工具（通过命名空间）
registry.register_namespace_tools(
    namespace="mcp:server1",
    tools={"remote_tool": mcp_tool}
)

# 获取工具
tool = registry.get("mcp:server1:remote_tool")
```
