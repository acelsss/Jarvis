# Planner 阶段文件访问机制说明

## 问题：这句话的含义

> "我们的系统：Planner 阶段 LLM 无文件系统访问，但可以在计划中包含读取步骤"

## 详细解释

### 1. Planner 阶段（计划生成阶段）

**位置**：`core/orchestrator/planner.py::create_plan()`

**作用**：LLM 根据任务描述和 skill 内容，生成一个执行计划（Plan）

**Plan 结构**：
```python
Plan(
    plan_id="plan_xxx",
    steps=[
        PlanStep(
            step_id="step_1",
            tool_id="file",
            description="读取引用文件",
            params={
                "operation": "read",
                "path": "skills_workspace/skill-creator/references/workflows.md"
            }
        ),
        PlanStep(...),
    ]
)
```

### 2. "LLM 无文件系统访问"的含义

**在 Planner 阶段**：
- LLM 只是一个 API 调用（`llm_client.complete_json()`）
- LLM **不能直接**读取文件系统中的文件
- LLM **只能看到**传入的 prompt 内容（task description + skill_fulltext）

**对比 Claude Code**：
- Claude Code 中，Claude 有文件系统访问能力
- Claude 可以直接执行 `cat references/workflows.md` 来读取文件
- 这是真正的"按需加载"

### 3. "可以在计划中包含读取步骤"的含义

虽然 LLM 在 Planner 阶段不能直接读取文件，但可以：

1. **看到引用提示**：
   - SKILL.md 中包含 "See references/workflows.md"
   - LLM 知道有这个文件存在

2. **生成读取步骤**：
   - LLM 可以在生成的计划中添加一个步骤：
   ```json
   {
     "tool_id": "file",
     "description": "读取 workflows.md 参考文件",
     "params": {
       "operation": "read",
       "path": "skills_workspace/skill-creator/references/workflows.md"
     }
   }
   ```

3. **执行阶段读取**：
   - 计划生成后，进入执行阶段
   - Executor 执行这个步骤
   - 通过 FileTool 读取文件内容
   - 读取的内容可以用于后续步骤

## 完整流程示例

### 场景：使用 skill-creator 创建新 skill

#### 阶段 1：路由（Routing）
```
用户输入: "我想创建一个新的skill"
↓
LLM 路由 → 匹配到 skill-creator
```

#### 阶段 2：计划生成（Planning）

**输入给 LLM**：
```
任务描述: 我想创建一个新的skill
技能全文如下：
---
name: skill-creator
description: Guide for creating effective skills...
---

# Skill Creator
...
- **Multi-step processes**: See references/workflows.md for sequential workflows
- **Specific output formats**: See references/output-patterns.md for template patterns
...
```

**LLM 看到**：
- ✅ SKILL.md 的完整内容（17,701 字符）
- ✅ 提示："See references/workflows.md"
- ✅ 提示："See references/output-patterns.md"
- ❌ 但看不到 workflows.md 和 output-patterns.md 的实际内容

**LLM 生成的计划**：
```json
{
  "steps": [
    {
      "tool_id": "file",
      "description": "读取 workflows.md 了解工作流模式",
      "params": {
        "operation": "read",
        "path": "skills_workspace/skill-creator/references/workflows.md"
      }
    },
    {
      "tool_id": "file",
      "description": "创建新 skill 的 SKILL.md 文件",
      "params": {
        "operation": "write",
        "path": "skills_workspace/my-new-skill/SKILL.md",
        "content": "..."
      }
    }
  ]
}
```

#### 阶段 3：执行（Execution）

**Executor 执行计划**：

1. **步骤 1**：读取 workflows.md
   ```python
   FileTool.execute({
       "operation": "read",
       "path": "skills_workspace/skill-creator/references/workflows.md"
   })
   # 返回文件内容
   ```

2. **步骤 2**：使用读取的内容创建新文件
   - 可以使用步骤 1 读取的内容
   - 结合任务要求生成新的 SKILL.md

## 关键区别

### Claude Code 的方式（真正的按需加载）

```
Claude 看到 SKILL.md 中的 "See references/workflows.md"
↓
Claude 自己决定：我需要看这个文件
↓
Claude 直接执行：cat references/workflows.md
↓
Claude 立即看到文件内容
↓
Claude 继续处理任务
```

**特点**：
- Claude 有文件系统访问能力
- 可以随时读取文件
- 真正的"按需加载"

### 我们的系统（计划式按需加载）

```
LLM 看到 SKILL.md 中的 "See references/workflows.md"
↓
LLM 决定：我需要看这个文件
↓
LLM 在计划中添加一个"读取文件"的步骤
↓
计划生成完成
↓
执行阶段：Executor 执行"读取文件"步骤
↓
文件内容被读取，可用于后续步骤
```

**特点**：
- LLM 在 Planner 阶段没有文件系统访问能力
- 但可以在计划中"声明"需要读取的文件
- 执行阶段通过工具读取

## 实际代码位置

### Planner 生成计划
**文件**：`core/orchestrator/planner.py:273`
```python
llm_result = llm_client.complete_json(
    purpose="plan",
    system=system,  # 包含可用工具列表（包括 file 工具）
    user=user,      # 包含任务描述和 skill_fulltext
    schema_hint=PLAN_SCHEMA,
)
# LLM 返回的 steps 可能包含 file.read 操作
```

### Executor 执行计划
**文件**：`core/orchestrator/executor.py`（如果存在）
或通过 `tools/runner.py` 执行

### FileTool 读取文件
**文件**：`tools/local/file_tool.py:80-84`
```python
if operation == "read":
    content = path.read_text(encoding="utf-8")
    return {"content": content, "path": str(path)}
```

## 总结

**"Planner 阶段 LLM 无文件系统访问，但可以在计划中包含读取步骤"** 的意思是：

1. **Planner 阶段**：LLM 只是一个 API，不能直接读取文件
2. **但 LLM 很聪明**：看到 SKILL.md 中的引用提示后，知道需要读取这些文件
3. **生成计划时**：LLM 可以在计划中添加"读取文件"的步骤
4. **执行阶段**：通过 FileTool 实际读取文件内容
5. **结果**：实现了"按需加载"，虽然方式不同，但效果类似

这种方式虽然不如 Claude Code 的直接文件访问灵活，但在我们的架构中是合理的，因为：
- 保持了计划的可预测性
- 所有文件访问都通过工具，便于审计
- 符合我们的安全模型（所有操作都需要通过工具）
