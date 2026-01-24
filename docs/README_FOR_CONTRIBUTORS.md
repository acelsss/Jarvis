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

### 2.6 如何在 skill 中使用 python_run（脚本放 scripts/，产物写到 sandbox/）

如果 skill 需要执行 Python 脚本，可以使用 `python_run` 工具。

**约定（必须遵守）**：
- **脚本位置**：skill 如需可执行脚本，必须放在 `skill_dir/scripts/` 目录下
- **执行工具**：统一使用 `python_run` 工具执行脚本
- **工作目录**：执行时 `cwd` 强制为 `sandbox/` 根目录
- **产物位置**：脚本产生的文件必须写到 `sandbox/` 目录下（如 `sandbox/outputs/`）

**限制**：
- 脚本必须放在以下位置之一：
  - `skills_workspace/<skill-name>/scripts/*.py`
  - `sandbox/scripts/*.py`
- 脚本路径会经过 `realpath` 校验，防止路径逃逸
- 执行时 `cwd` 强制为 `sandbox/` 根目录
- 风险等级 R2（需要用户审批）

**元数据暴露**：
- `SkillsRegistry.list_skill_metadata()` 会自动扫描 `scripts/` 目录
- 脚本信息会包含在 capability index 中，供 LLM 路由和规划使用
- 只暴露脚本文件名和相对路径，不加载脚本内容（保持 progressive disclosure）

**示例**：

在 skill 的 SKILL.md 中，可以这样描述：

```markdown
## 执行步骤

1. 使用 python_run 工具执行初始化脚本：
   - tool_id: `python_run`
   - params:
     ```json
     {
       "script_path": "skills_workspace/my-skill/scripts/init.py",
       "args": ["--output", "sandbox/outputs/result.txt"],
       "timeout_seconds": 60
     }
     ```

2. 脚本执行后，产物会写入 `sandbox/` 目录
```

**注意事项**：
- 脚本执行时的工作目录（cwd）是 `sandbox/` 根目录
- 脚本应该将输出文件写入 `sandbox/` 下的子目录（如 `sandbox/outputs/`）
- 脚本路径使用相对路径（相对于项目根目录）
- 超时时间默认 60 秒，上限 120 秒
- stdout/stderr 会被截断到 2048 字符（避免日志爆炸）

**审计日志**：
- 所有 `python_run` 执行都会记录到 `audit.log.jsonl`
- 事件类型：`tool.python_run`
- 记录字段：`script_path_relative`, `args`, `cwd`, `timeout_seconds`, `exit_code`, `stdout_len`, `stderr_len`, `duration_ms`

---

## 3) Prompt 管理规范

### 3.1 硬要求（必须遵守）

#### 3.1.1 存放位置
- **所有 LLM prompt 必须存放在 `prompts/` 目录下**
- **禁止在代码中新增超过 15 行的硬编码 prompt 文本**
- 超过 15 行的 prompt 必须提取到 `prompts/` 目录下的 `.md` 文件

#### 3.1.2 YAML Frontmatter（必需字段）
每个 prompt 文件必须包含完整的 YAML frontmatter，至少包含以下字段：

```yaml
---
id: router/llm_first          # prompt_id（文件路径，不含 .md）
name: router_llm_first        # 人类可读名称
version: 1.0.0                # 版本号（语义版本或递增）
used_by:                      # 使用位置列表
  - core/router/route.py::route_llm_first()
inputs:                        # 输入变量声明
  - route_schema: RouteDecision schema 字符串
  - capability_index_json: 能力索引摘要 JSON
output:                        # 输出约束
  type: json                  # json 或 text
  schema_fields:              # JSON 输出时必需字段（可选）
    - route_type
    - confidence
    - skill_id
  constraints: []             # 额外约束（如 ["No tool calls"]）
---
```

**必需字段说明**：
- `id`: prompt 的唯一标识符，通常是文件路径（不含 `.md` 扩展名）
- `name`: 人类可读的名称
- `version`: 版本号，每次修改必须更新
- `used_by`: 使用该 prompt 的代码位置列表
- `inputs`: 所有在 prompt 中使用的 `{{var}}` 变量必须在此声明
- `output.type`: 必须是 `json` 或 `text`
- `output.schema_fields`: 当 `output.type=json` 时，列出必需字段（可选但推荐）
- `output.constraints`: 额外约束说明（如禁止工具调用等）

#### 3.1.3 Role 分段结构
每个 prompt 文件必须包含明确的 role 分段：

```markdown
## system

你是路由助手。
只返回符合 RouteDecision schema 的 JSON。
...

## user

用户输入: {{task_text}}
...
```

**要求**：
- 必须包含 `## system` 分段
- 可选包含 `## user` 分段
- 可选包含 `## assistant` 分段（用于 few-shot 示例）
- 禁止使用 `---` 作为分隔符（与 YAML frontmatter 冲突）

#### 3.1.4 变量声明与渲染
- **所有 `{{var}}` 变量必须在 frontmatter.inputs 中声明**
- **render 默认 strict 模式**：如果提供了未声明的变量，应该警告（未来版本可能报错）
- **如果 prompt 中使用了 `{{var}}` 但 inputs 中未声明，校验会失败**

#### 3.1.5 输出约束
根据 prompt 类型，必须声明相应的输出约束：

**Router/Planner 类（JSON 输出）**：
```yaml
output:
  type: json
  schema_fields:
    - route_type
    - confidence
    - skill_id
```

**Chat/QA 类（文本输出）**：
```yaml
output:
  type: text
  constraints:
    - "No tool calls"
```

#### 3.1.6 Prompt ID 稳定性
- **代码引用以 prompt_id（文件路径）为准，禁止随意改名**
- **如需新版本**：使用 `*_v2.md` 命名并保留旧版本以便回滚
- **迁移流程**：先添加新文件 → 更新代码引用 → 运行测试 → 删除旧文件

### 3.2 推荐项（强烈建议）

#### 3.2.1 公共片段复用
- 将公共 prompt 片段放在 `prompts/_shared/` 目录
- 尽量复用，避免复制粘贴
- 示例：工具约束说明、JSON schema 说明等

#### 3.2.2 Model Hints（可选）
在 frontmatter 中声明模型参数建议（不强制解析，但作为治理依据）：

```yaml
model_hints:
  temperature: 0.7
  max_tokens: 2000
```

#### 3.2.3 版本管理
- 每次修改 prompt 必须更新 `version` 字段
- 建议使用语义版本（如 `1.0.0` → `1.0.1`）或递增版本号

### 3.3 禁止项（严格禁止）

#### 3.3.1 复杂条件语法
- **禁止在 prompt 内写复杂条件语法**（如 `{{#if}}`, `{{#each}}` 等）
- **条件逻辑必须放在代码中**，通过不同的 prompt 文件或变量值来处理

#### 3.3.2 Provider 私有字段
- **禁止 prompt 绑定某一 provider 的私有字段**（如 OpenAI 的 `system_message` 格式）
- 除非在文档中明确说明，并在代码中提供兼容层

#### 3.3.3 高风险系统动作
- **禁止 prompt 引导执行高风险系统动作**（如删除文件、执行命令）
- 所有高风险操作必须通过 tool + 风险门控机制

### 3.4 变更流程

#### 3.4.1 新增/修改 Prompt 的标准流程
1. **编辑 prompt 文件**：在 `prompts/` 对应目录下创建/修改 `.md` 文件
2. **更新 frontmatter**：确保所有必需字段齐全，更新 `version`
3. **运行校验测试**：执行 `python -m pytest tests/test_prompts.py` 确保通过
4. **运行最小回归**：CLI 跑一条路由/规划/QA 任务，验证行为
5. **提交代码**：确保所有测试通过后再提交

#### 3.4.2 JSON 输出 Prompt 的特殊要求
对于 `output.type=json` 的 prompt：
- **必须能 JSON parse**：提供测试数据后，LLM 输出必须能成功解析为 JSON
- **必须包含必需字段**：解析后的 JSON 必须包含 `output.schema_fields` 中声明的所有字段
- **建议添加测试用例**：在 `tests/test_prompts.py` 中添加针对性的测试

### 3.5 测试要求（强制）

所有 prompt 必须通过以下测试：

#### 3.5.1 Prompt 存在性测试
- 所有代码中引用的 `prompt_id` 必须能成功 `load()`
- 测试位置：`tests/test_prompts.py::test_all_prompts_loadable()`

#### 3.5.2 Prompt 渲染测试
- 提供完整的 `vars` 后，`render()` 结果不应残留任何 `{{...}}` 占位符
- 测试位置：`tests/test_prompts.py::test_prompt_rendering()`

#### 3.5.3 结构校验测试
- Frontmatter 必需字段齐全（id, name, version, used_by, inputs, output）
- 必须包含 `## system` 分段
- 所有 `{{var}}` 变量都在 `inputs` 中声明
- 测试位置：`tests/test_prompts.py::test_prompt_structure()`

#### 3.5.4 运行测试
```bash
# 运行所有 prompt 测试
python -m pytest tests/test_prompts.py -v

# 运行特定测试
python -m pytest tests/test_prompts.py::test_all_prompts_loadable -v
```

### 3.6 目录结构

```
prompts/
  _shared/           # 共享的 prompt 片段（如工具约束说明）
    TEMPLATE.md      # 标准模板（参考用）
  router/            # 路由相关的 prompts
    llm_first.md
    rule_fallback.md
  planner/           # 规划相关的 prompts
    default.md
  chat/              # 对话/问答相关的 prompts
    qa.md
  skills/            # 技能注入模板（如需要）
  tools/             # 工具调用相关的 prompts（如需要）
```

### 3.7 如何使用 PromptLoader

在代码中使用 `PromptLoader` 加载 prompt：

```python
from core.prompts.loader import PromptLoader

loader = PromptLoader()
prompt_template = loader.load("router/llm_first.md")

# 解析 role 分段（## system, ## user 等）
# 注意：代码中需要实现解析逻辑，提取 ## system 和 ## user 部分

# 渲染变量
system = loader.render(system_template, {
    "route_schema": ROUTE_SCHEMA_V0_2,
    "capability_index_json": json.dumps(index, ensure_ascii=False),
})
user = loader.render(user_template, {
    "task_text": task_text,
    "context_summary_json": json.dumps(context, ensure_ascii=False),
})
```

### 3.8 验收清单

在提交 prompt 相关代码前，请确认：

- [ ] 所有 LLM prompt 都已存放在 `prompts/` 目录
- [ ] 代码中不再有超过 15 行的硬编码 prompt 字符串
- [ ] Prompt 文件包含完整的 YAML frontmatter（所有必需字段）
- [ ] Prompt 文件包含 `## system` 分段
- [ ] 所有 `{{var}}` 变量都在 `inputs` 中声明
- [ ] `output.type` 正确声明（json 或 text）
- [ ] 运行 `pytest tests/test_prompts.py` 全部通过
- [ ] CLI 运行一次任务，输出与预期一致

---

## 4) 如何新增/修改 Router 规则（意图分发）

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

## 5) 开发规范（强烈建议遵守）

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

## 6) 常见问题（FAQ）

### Q1: 我能不能在 Skill 里直接写 bash 然后执行？
v0.1 不允许。Skill 是流程资产，执行必须通过 ToolRunner，且受风险门控。

### Q2: 我想接一个第三方“操作电脑”的项目怎么办？
把它封装成 Tool（例如 `local.desktop.click` / `local.desktop.type`），默认风险至少 R2，并输出截图证据。

### Q3: Router 越写越复杂怎么办？
把复杂判断下放到 “Planner/SkillMatch”，Router 只做粗分发；必要时引入 LangGraph 作为 planner，但不要破坏 contracts。

### Q4: 如何集成外部 Agent 或 CLI 工具（如 OpenCode、Aider 等）？
统一通过 Tool 接口接入，遵循以下原则：
- 创建专用 Tool（如 `opencode_run`），不要使用通用 shell 工具
- 默认风险等级至少 R2，会修改代码的建议 R3
- 工作目录限制在 `sandbox/workspaces/` 下，禁止直接操作真实工程目录
- 完整的审计日志（事件类型、参数摘要、执行结果、变更文件列表）
- 产物差分：执行前后快照对比，输出 `changed_files` 清单

参考示例：[INTEGRATION_OPENCODE_CLI.md](INTEGRATION_OPENCODE_CLI.md)（OpenCode CLI 集成设计文档）
更多扩展点说明：[EXTENSION_POINTS.md](EXTENSION_POINTS.md#44-tool-providers可扩展)
