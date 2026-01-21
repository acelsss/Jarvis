# Task Contract v0.1

## 概述

任务契约定义了任务的基本结构和生命周期。

## 契约字段

- `task_id`: 唯一任务标识
- `description`: 任务描述
- `status`: 任务状态（new, context_built, planned, waiting_approval, approved, running, completed, failed）
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `context`: 任务上下文数据
- `artifacts`: 产物路径列表
- `actions`: 执行的动作记录

## 状态流转

```
new → context_built → planned → waiting_approval → approved → running → completed
                                                                    ↓
                                                                 failed
```

### 状态说明

- `new`: 任务已创建，初始状态
- `context_built`: 上下文已构建（身份配置、OpenMemory 搜索结果等）
- `planned`: 执行计划已生成
- `waiting_approval`: 等待审批（当计划包含 R2 或 R3 风险等级时）
- `approved`: 审批通过，可以执行
- `running`: 正在执行
- `completed`: 执行完成
- `failed`: 执行失败

## v0.1 实现

- 使用 dataclass 定义
- 基础状态管理
- 时间戳追踪

## 向后兼容说明

**注意**：旧版本文档中可能出现的状态名称（如 `pending`）已废弃。请以代码契约 `core/contracts/task.py` 中定义的状态为准。
