# Task Contract v0.1

## 概述

任务契约定义了任务的基本结构和生命周期。

## 契约字段

- `task_id`: 唯一任务标识
- `description`: 任务描述
- `status`: 任务状态（pending, approved, running, completed, failed）
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `context`: 任务上下文数据

## 状态流转

```
pending → approved → running → completed
                ↓
             failed
```

## v0.1 实现

- 使用 dataclass 定义
- 基础状态管理
- 时间戳追踪
