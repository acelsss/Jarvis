# Jarvis v0.1

## 项目概述

Jarvis 是一个基于契约驱动的智能任务编排系统，v0.1 版本聚焦于最小可用的核心闭环。

## v0.1 目标

实现以下核心功能的闭环：

- **Task**: 任务契约定义与生命周期管理
- **Tool**: 工具契约与执行框架
- **Memory**: 记忆存储与检索机制
- **Risk**: 风险审批门控
- **Audit**: 审计日志与合规追踪
- **CLI**: 命令行交互界面

## 技术栈

- Python 3.11+
- dataclasses (contracts)
- pyyaml (配置文件解析)

## 项目结构

```
jarvis/
├── README.md
├── pyproject.toml
├── .env.example
├── docs/              # 架构文档与契约规范
├── identity_pack/     # 身份配置包
├── core/              # 核心引擎
├── tools/             # 工具实现
├── skills/            # 技能适配器
├── memory/            # 记忆存储
└── apps/              # 应用入口
```

## 快速开始

```bash
# 安装依赖
pip install -e .
# 或直接安装 pyyaml
pip install pyyaml

# 运行 CLI
python -m apps.cli.main

# 或直接传入任务描述
python -m apps.cli.main "创建一个测试文件"
```

## 运行说明

详细运行说明和示例输出请参考：
- [RUNNING.md](RUNNING.md) - 运行说明
- [EXAMPLE_OUTPUT.md](EXAMPLE_OUTPUT.md) - 示例运行输出
- [SKILLS_USAGE.md](SKILLS_USAGE.md) - Skills 子系统使用说明

## 开发状态

v0.1 - Kernel MVP 最小闭环已实现，支持：
- ✅ Task/Tool/Memory/Risk/Audit 核心契约
- ✅ CLI 完整闭环流程
- ✅ 上下文构建（identity_pack + OpenMemory stub）
- ✅ 简单规则路由（支持技能匹配）
- ✅ 计划生成（2-3 步骤，包含 file_tool）
- ✅ 风险审批门控（R2 及以上需要审批）
- ✅ 工具执行与结果记录
- ✅ 审计日志（JSONL 格式）
- ✅ **Skills 子系统** - 技能注册、解析、计划生成

## Skills 子系统

v0.1 新增 Skills 子系统，支持：

- **技能注册** - 自动扫描 `skills_workspace/` 目录
- **技能解析** - 支持 Claude Code 风格的 SKILL.md（YAML frontmatter + Markdown）
- **计划转换** - 将技能指令转换为可执行的 PlanStep
- **智能匹配** - 根据任务描述自动匹配技能
- **安全执行** - v0.1 禁止技能执行脚本，只通过 ToolRunner 执行受控工具

快速体验：

```bash
# 查看已加载的技能
python -m apps.cli.main
# 输入: /skills

# 触发技能执行
python -m apps.cli.main "生成一篇关于Python的微信公众号文章"
```

详细说明请参考 [SKILLS_USAGE.md](SKILLS_USAGE.md)

## 扩展接口

v0.1 定义了以下扩展接口（仅接口和 stub 实现）：

- **OpenMemory 适配器** - 记忆系统集成接口（`tools/local/openmemory_stub.py`）
- **MCP 客户端** - Model Context Protocol 集成接口（`tools/mcp/mcp_client.py`）
- **工具注册表命名空间** - 支持外部工具组注册（如 `mcp:server:tool`）

所有接口都提供 stub 实现，便于未来真实集成。详细说明请参考：
- [docs/EXTENSION_POINTS.md](docs/EXTENSION_POINTS.md) - 扩展点详细说明
- [docs/architecture.md](docs/architecture.md) - 架构文档（包含扩展点说明）
