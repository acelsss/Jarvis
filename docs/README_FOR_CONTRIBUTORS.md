# README for Contributors

本文件面向：使用 Cursor 参与开发的协作者 / 未来的你。目标是让任何人以一致的工程方式扩展 Jarvis，而不是把逻辑散落在各处。

> 原则：新增能力优先做成 **Tool** 或 **Skill**；Router 只负责“选择哪条路”，不写业务细节；任何执行都必须走 **Risk Gate + Audit**。

---

## 0. 约定与目录

- **Contracts（不可随意破坏）**：`core/contracts/`
- **执行与编排**：`core/orchestrator/`
- **路由（轻逻辑）**：`core/router/`
- **工具（动作能力）**：`tools/`
- **技能（流程资产）**：`skills/` + `skills_workspace/`
- **身份与偏好（人格/策略）**：`identity_pack/`
- **审计日志（事实）**：`memory/raw_logs/`

---

## 1) 如何新增一个 Tool（动作能力）

### 1.1 适用场景
当你要让 Jarvis “做一件具体的事”，例如：
- 写/读 sandbox 文件
- 调用 HTTP API（未来）
- 调用 MCP server（未来）
- 电脑操作（未来）
都应实现为 Tool。

### 1.2 步骤（最短路径）
1. 在 `tools/local/`（或未来的 `tools/mcp/`）新增实现文件，例如：
   - `tools/local/my_tool.py`
2. 在 `tools/registry.py` 注册该工具（或通过自动扫描机制，如果未来引入）。
3. 为工具定义清晰的：
   - `tool_id`（唯一）
   - `description`
   - `risk_level`（R0–R3）
   - 参数 schema（v0.1 允许轻量，不要引入 heavy 依赖）

### 1.3 必须满足的约束（硬约束）
- **所有有副作用的工具**必须输出 `ToolResult` 并提供 `evidence_refs`（例如文件路径、截图路径、响应摘要）。
- **任何风险 ≥ R2 的工具**必须触发审批（由 `ApprovalGate` 决定），禁止旁路。
- 默认禁止直接执行任意 shell（v0.1 `ShellTool` 仅允许白名单 `echo`）。

### 1.4 最小示例（伪代码）
```python
class MyTool:
    tool_id = "local.my_tool"
    risk_level = "R1"

    def run(self, args, context) -> ToolResult:
        # ... do something ...
        return ToolResult(ok=True, output={"...": "..."}, evidence_refs=[...])
```

### 1.5 验收清单
- CLI 跑通：`python -m apps.cli.main`
- 输入触发路由后能执行该 tool
- 审计日志 `memory/raw_logs/audit.log.jsonl` 有记录
- 若 risk>=R2，必须询问确认

---

## 2) 如何新增一个 Skill（流程资产）

### 2.1 Skill 是什么
Skill 不是“直接执行脚本”，而是一个 **可复用的工作流说明**。它会被解析为 Plan，再由 ToolRunner 执行。

> v0.1 禁止 skills 直接执行脚本（防止绕过风险门控）。

### 2.2 最短路径：新增一个本地 skill
1. 在 `skills_workspace/` 新建目录：
   - `skills_workspace/my_skill/`
2. 新建 `SKILL.md`，采用 Claude Code 风格：顶部 YAML frontmatter + Markdown body。
3. 在正文中写清“目标、步骤、输入输出、注意事项、风险点”。

**推荐 frontmatter 字段：**
- `name`（必须）
- `description`（建议单行）
- `tags`（列表）
- `version`（可选）

示例：
```md
---
name: wechat_article
description: Draft a WeChat article from bullet points and references.
tags: [writing, wechat, content]
version: 0.1
---

## Goal
...

## Steps
1) ...
2) ...

## Outputs
- ...
```

### 2.3 如何让 Skill 被加载
- `skills/registry.py` 会扫描 `skills_workspace/` 并尝试用 adapter 解析。
- v0.1 主要支持 `skills/adapters/claude_code_adapter.py`。

### 2.4 Skill 如何变成可执行计划
- `skills/runtime/to_plan.py` 将 Skill Markdown 变成 `Plan`（PlanStep）。
- 执行仍走 ToolRunner：PlanStep 会映射为具体 tool 调用（例如 `local.file.write` 等）。

### 2.5 验收清单
- CLI 输入 `/skills` 能看到新技能
- 输入能触发 skill 匹配并生成 plan
- plan 中至少一个步骤落地产物到 sandbox（便于闭环）

---

## 3) 如何新增/修改 Router 规则（意图分发）

### 3.1 Router 的职责边界
Router 只做：
- 识别意图类型（qa / task / skill / self_update / …）
- 决定走哪条 handler / orchestrator 流程
- 选择 skill（若匹配）

Router 不做：
- 具体业务逻辑
- 直接执行工具
- 直接读写文件（应由 Tool 完成）

### 3.2 最短路径
1. 修改 `core/router/route.py`（或相应 router 文件）
2. 增加一个轻量规则（keyword/regex/简单模式）
3. 返回标准的 route result（例如 `RouteDecision(kind="skill", skill_id=...)`）

> 注意：v0.1 以“规则优先、LLM fallback”为建议路线，但如果你暂未引入 LLM，也应保持接口可插拔。

### 3.3 验收清单
- 不破坏现有 route
- 至少新增一个测试输入能稳定命中规则
- 走到 planner/approval/execute 全链路

---

## 4) 开发规范（强烈建议遵守）

### 4.1 “一件事一个 commit”
- 新增 Tool：一个 commit
- 新增 Skill：一个 commit
- 改 Router：一个 commit
- 改契约/风险：一个 commit

### 4.2 不要把“事实”写进 OpenMemory
- OpenMemory 是索引（可替换）
- 事实应写到：Task DB / Audit Log / Artifact 文件

### 4.3 所有副作用动作必须可复盘
- 产物路径可定位
- 参数摘要可定位
- 风险审批可定位

---

## 5) 常见问题（FAQ）

### Q1: 我能不能在 Skill 里直接写 bash 然后执行？
v0.1 不允许。Skill 是流程资产，执行必须通过 ToolRunner，且受风险门控。

### Q2: 我想接一个第三方“操作电脑”的项目怎么办？
把它封装成 Tool（例如 `local.desktop.click` / `local.desktop.type`），默认风险至少 R2，并输出截图证据。

### Q3: Router 越写越复杂怎么办？
把复杂判断下放到 “Planner/SkillMatch”，Router 只做粗分发；必要时引入 LangGraph 作为 planner，但不要破坏 contracts。
