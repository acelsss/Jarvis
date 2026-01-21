# Memory Contract v0.1

## 概述

记忆契约定义了记忆的存储结构和检索接口。

## 记忆类型

- `task_db`: 任务数据库（结构化）
- `distilled`: 精炼记忆（摘要）
- `raw_logs`: 原始日志（审计）

## 存储结构

- `memory_id`: 记忆唯一标识
- `content`: 记忆内容
- `metadata`: 元数据（时间、来源等）
- `tags`: 标签（用于检索）

## v0.1 实现

- 文件系统存储（JSON）
- 基础检索接口
- 任务关联
