# Skills Specification v0.1

## 概述

技能规范定义了技能的适配接口和运行时行为。

## 技能适配器

- `claude_code_adapter`: Claude Code 技能适配
- `agentskills_adapter`: Agent Skills 适配

## 技能接口

```python
async def plan(task: Task) -> Plan:
    """将任务转换为执行计划"""
    pass
```

## v0.1 实现

- 适配器框架
- 计划生成接口
- 运行时转换
