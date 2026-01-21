# Extension Points & Compatibility Contract

本文件定义 **Jarvis 的稳定内核（Kernel API Contract）** 与 **可替换扩展点（Pluggable Layers）**。

目标：无论未来更换模型、重写 planner、替换记忆系统、接入 MCP 或电脑操作，**Jarvis 仍然是同一个 Jarvis**，且历史数据与技能资产尽量不失效。

---

## 0. 核心定义

- **Facts（事实）**：任务、动作、产物、审批、审计日志。必须可复盘、可追踪。
- **Index（索引）**：为 recall 提供检索能力（如 OpenMemory）。可替换，不应成为事实源。
- **Kernel**：以 Contracts + 执行链 + 风险门控 + 审计为核心的稳定层。

---

## 1. Non-negotiables（永不旁路的硬规则）

1) **所有执行必须通过 ToolRunner**
- 不允许从 Skill/Router/Planner 直接执行副作用动作
- 工具调用必须产生 ToolResult

2) **Risk Gate 必须生效**
- risk >= R2 必须审批
- 高风险动作必须输出证据与回滚点（未来）

3) **Audit Log 必须完整**
- 每次 tool 调用：输入摘要、输出摘要、耗时、审批、证据引用
- 日志格式：JSONL（逐行 JSON）

4) **Facts 与 Index 分离**
- 事实写入：Task DB / Audit / Artifacts
- Index（OpenMemory）只存可检索摘要或向量索引

---

## 2. Stable Contracts（稳定契约）

这些文件的语义是 Kernel API 的核心，未来变更要遵循“向后兼容优先”：

- `core/contracts/task.py`
  - Task ID、状态机语义、Action/Artifact 结构
- `core/contracts/tool.py`
  - ToolSpec、ToolResult、evidence_refs
- `core/contracts/risk.py`
  - 风险等级（R0–R3）与含义
- `core/contracts/memory.py`
  - MemoryItem 的抽象（facts/index 的边界约束）
- `core/contracts/skill.py`
  - JarvisSkill、Plan、PlanStep 的最小字段集合

### 2.1 兼容性原则
- **字段新增**：允许（提供默认值）
- **字段重命名/删除**：禁止直接做；必须提供迁移层并保留旧字段一段时间
- **状态语义变更**：必须提供迁移/回放策略，并更新 docs/contracts

---

## 3. Execution Chain Contract（执行链协议）

Jarvis 的标准执行链为：

1) **Input Normalize**
2) **Context Build**
   - 读取 Identity Pack
   - Recall：Index（OpenMemory）检索 top-k 相关内容（可选）
3) **Route**
   - 识别意图类型（qa/task/skill/…）
4) **Plan**
   - 生成 Plan（PlanStep 列表）
5) **Risk Gate**
   - 对每个 PlanStep 评估 risk_level
   - >= R2 必须进入 approval 流
6) **Execute**
   - ToolRunner 执行 step（统一日志与证据）
7) **Audit**
   - 写入 JSONL 审计
8) **Writeback**
   - 将结果写入 Facts（Task DB / Artifacts）
   - 可选写入 Index（摘要）

任何未来的重构（引入 LangGraph、多 agent、并行等）都必须保持以上链条的语义可映射。

---

## 4. Pluggable Layers（可替换层）

以下层可替换/升级，但必须遵守稳定契约：

### 4.1 LLM Provider（可替换）
- OpenAI / DeepSeek / local models / 未来模型
- 只影响：Route/Plan/Reflect 的“智能生成”
- 不允许影响：Risk Gate、Audit、ToolRunner

### 4.2 Planner / Orchestrator（可替换）
- 规则 planner → LangGraph → 多代理协作
- 必须输出：Plan（PlanStep）
- 必须可插入审批点

### 4.3 Memory Index（可替换）
- OpenMemory / Chroma / FAISS / 自研向量库
- 只做 recall/upsert
- 不应存储事实全量

### 4.4 Tool Providers（可扩展）
- local tools（Python）
- MCP tools（远程）
- desktop operator tools（本地高权限）

要求：
- ToolSpec/ToolResult 统一
- risk_level 可评估
- evidence_refs 可定位

### 4.5 Interfaces（可扩展）
- CLI / Voice / Webhook / WeChat / GUI
- 输入输出可变，但必须进入统一执行链

---

## 5. Identity Pack Contract（人格与长期一致性）

Identity Pack 是“Jarvis 还是 Jarvis”的关键资产，应该：
- 版本化（`identity_pack/version.json`）
- 可迁移（提供迁移脚本或说明）
- 与代码弱耦合（读取配置，不写死在代码里）

建议长期保持这些文件存在并语义稳定：
- `constitution.yaml`：原则/红线
- `voice_style.yaml`：风格与表达
- `preferences.yaml`：默认偏好（sandbox_root、默认语言等）
- `memory_policy.yaml`：记忆写回策略

---

## 6. Data Compatibility（数据兼容承诺）

Jarvis 的历史资产包括：
- Audit logs（JSONL）
- Task DB（未来可能是 jsonl/sqlite）
- Artifacts（sandbox 文件）
- Skills（SKILL.md）

兼容承诺：
- 新版本必须能读取旧版本的 Audit JSONL（至少不崩溃）
- Task DB 若变更存储形态，必须提供迁移脚本
- Skills 解析器应尽量兼容 Claude Code 风格 frontmatter

---

## 7. Versioning（建议的版本策略）

- **v0.x**：允许快速演进，但必须保持 contracts 基本字段集合稳定
- **v1.0**：冻结 contracts 主语义与执行链协议；引入严格迁移与兼容测试

---

## 8. Checklist（扩展点自检清单）

当你要接入一个新能力（Tool/Skill/MCP/Desktop）时，请逐项确认：

- [ ] 是否定义了 ToolSpec（tool_id/params/risk）？
- [ ] 是否所有副作用动作走 ToolRunner？
- [ ] 是否 risk>=R2 会触发审批？
- [ ] 是否产出 evidence_refs（文件/截图/响应摘要）？
- [ ] 是否写入审计 JSONL？
- [ ] 是否 Facts 与 Index 分离（不把事实塞进索引）？
