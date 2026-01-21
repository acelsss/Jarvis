# Tool Contract v0.1

## 概述

工具契约定义了工具的执行接口和元数据。

## 契约字段

- `tool_id`: 工具唯一标识
- `name`: 工具名称
- `description`: 工具描述
- `parameters`: 参数定义（JSON Schema）
- `risk_level`: 风险等级（low, medium, high）
- `requires_approval`: 是否需要审批

## 执行接口

```python
async def execute(params: dict) -> dict:
    """执行工具并返回结果"""
    pass
```

## v0.1 实现

- 基础工具注册机制
- 参数验证
- 执行结果封装
