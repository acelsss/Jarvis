# Jarvis

一个可演进的个人智能助理内核（Kernel MVP），目标是把"像钢铁侠 Jarvis 一样什么都能做"的愿景，落成可控、可扩展、可审计的软件工程系统。

核心思路：

- **Identity Pack**：人格/原则/偏好/记忆策略（保证升级后依旧"是同一个 Jarvis"）
- **Kernel**：任务/工具/记忆/风险/审计 的稳定契约（保证可控、可复盘、可持续演进）
- **Plugins**：Skills（流程资产）、Tools（动作能力）、MCP（工具接入标准）、Interfaces（入口）

---

## Why Jarvis (Engineering-first)

如果只做一个"会聊天的 Agent"，随着能力增多很快会变成：
- 逻辑散落各处、难以复用
- 风险动作不可控（文件、网络、账号、支付）
- 无法追踪"做过什么、为什么这么做、产物在哪里"

Jarvis 选择工程化路线：**先把内核做稳，再不断外挂能力**。

---

## What You Get (v0.1)

v0.1 聚焦于 **Kernel MVP 最小闭环**：

- **Context Engine**：读取 Identity Pack +（可选）OpenMemory 检索相关记忆，形成上下文包
- **Router**：基于规则做最小路由（qa/task/skill/self_update…）
- **Task**：将意图落为可追踪任务（含计划、步骤、动作记录、产物索引）
- **Risk Gate (R0–R3)**：中高风险动作需要用户确认
- **Tool Runner**：统一执行工具并产生日志/证据
- **Audit Log**：关键决策与工具调用全链路审计（JSONL）

> v0.1 的目标不是"聪明"，而是"可跑通 + 可控 + 可扩展"。

---

## Architecture (High Level)

**Input → Context → Route → Plan → Approval → Execute → Audit → Writeback**

- **Facts**：任务事实与动作记录（Task / Action / Artifact）由 Jarvis 自己保存
- **Index**：OpenMemory 作为检索索引（可替换），不作为事实源
- **Skills**：第三方/本地技能只提供"流程资产"，执行必须走 Tool Runner + Risk Gate

---

## Repository Layout

```text
apps/cli/                 # v0.1 入口（CLI）
core/
  contracts/              # Task/Tool/Risk/Memory/Skill 契约（内核稳定点）
  context_engine/         # Identity + OpenMemory recall → ContextBundle
  router/                 # 最小路由
  orchestrator/           # planner / approval_gate / executor / task_manager
  platform/               # audit/config/secrets 占位与基础设施
tools/
  registry.py             # 工具注册
  runner.py               # 工具执行统一入口
  local/                  # file/shell/openmemory_stub 等本地工具
  mcp/                    # MCP 接入占位（未来扩展点）
skills/
  registry.py             # 扫描本地 skills_workspace
  adapters/               # Claude Code / AgentSkills 解析适配
  runtime/                # Skill → Plan 的转换（执行仍走 Tool Runner）
identity_pack/            # Jarvis 身份资产（可迁移、不随代码轻易变化）
memory/
  task_db/                # 任务事实存储（v0.1 可先简化，后续可升级 SQLite）
  distilled/              # 提炼记忆（可选）
  raw_logs/               # 审计日志、证据引用、运行日志等
docs/                     # 规格与ADR
```

---

## Risk Model (R0–R3)

- **R0**：只读/纯生成，无副作用（可自动）
- **R1**：低风险副作用（写入 sandbox、新建文件）（自动 + 必须审计）
- **R2**：中风险（运行未知代码、安装依赖、修改配置）（需要一次确认）
- **R3**：高风险（删除/覆盖、对外发布、涉及账号/支付/密钥、生产环境）（二次确认 + 影响范围 + 回滚点）

默认策略：**保守**。任何可能不可逆的动作都必须明确确认。

---

## Skills (Workflow Assets)

Jarvis 采用"技能=流程资产"的模式：

- Skills 负责提供结构化工作流（例如写公众号、安装 GitHub 项目、生成报告）
- 执行仍由 Jarvis 内核编排：**Skill → Plan → Tool Calls**
- v0.1 默认禁止 skills 直接执行脚本（防止旁路风险门控）

### Supported (v0.1)
- Claude Code 风格：`SKILL.md`（YAML frontmatter + Markdown body）
- AgentSkills：预留适配器（stub）

---

## Quick Start

### 1) 环境准备
- Python 3.11+
- （可选）安装 YAML 解析依赖：
  - `pip install pyyaml`

### 2) 配置
复制环境变量模板：
```bash
cp .env.example .env
```

检查/设置 sandbox（默认在 `~/JarvisSandbox` 或 identity_pack 配置）：
```bash
mkdir -p ~/JarvisSandbox
```

### 3) 运行 CLI
```bash
python -m apps.cli.main
```

常用：
- 输入任意文本：创建 task、生成 plan、必要时询问审批、执行工具并落盘产物
- `/skills`：列出已加载 skills

---

## Design Guarantees (Non-negotiables)

这些是为了确保"升级后还是同一个 Jarvis"的稳定锚点：

1. **Contracts 稳定**：Task/Tool/Risk/Memory/Audit 的数据结构与语义不随意破坏
2. **Risk Gate 不旁路**：任何执行能力必须走统一执行器与审计
3. **Identity Pack 可迁移**：人格/偏好/策略不与代码强耦合，可版本化迁移
4. **Facts 与 Index 分离**：事实源在 Jarvis，检索索引可替换

---

## Documentation

- **[docs/README_FOR_CONTRIBUTORS.md](docs/README_FOR_CONTRIBUTORS.md)** - 贡献者指南：面向使用 Cursor 参与开发的协作者，提供一致的工程方式扩展 Jarvis 的指导
- **[docs/EXTENSION_POINTS.md](docs/EXTENSION_POINTS.md)** - 扩展点与兼容性契约：定义 Jarvis 的稳定内核（Kernel API Contract）与可替换扩展点（Pluggable Layers）

---

## Roadmap

### v0.1.1（对齐与收口）
- 统一 docs 与代码的状态机/风险等级
- Task DB 最小落盘（jsonl 或 sqlite）
- SkillsRegistry 读取 identity_pack/skills_profile.yaml 控制启用源
- Plan/Task JSON-safe 序列化（便于审计与回放）

### v0.2（可插拔能力增强）
- MCP 工具接入（list/call 工具，统一权限与风险）
- OpenMemory 真正适配（search/upsert），加写回策略（reflect）
- 更强的 planner（可选 LangGraph）与可恢复执行（checkpoint）

### v0.3（Desktop Operator）
- 电脑操作工具域（desktop_control），默认 R2/R3
- 屏幕证据与回滚策略（截图/录屏/操作日志）
- "先 dry-run 再执行"的交互范式

### Integrations（外部工具集成）

- **OpenCode CLI 集成（A 线路）**：通过 CLI 调用 OpenCode 执行编码任务
  - 设计文档：[docs/INTEGRATION_OPENCODE_CLI.md](docs/INTEGRATION_OPENCODE_CLI.md)
  - 状态：设计完成，待实施
  - 风险等级：R3（会修改代码、执行命令）

---

## Notes

- 本项目优先追求"可控性与可复盘"，而不是一次性堆满功能
- 任何可能带来不可逆影响的能力（删除、对外发送、真实交易、生产操作）默认关闭或需要高等级审批
