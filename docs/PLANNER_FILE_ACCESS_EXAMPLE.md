# Planner 阶段文件访问机制 - 实际示例

## 问题解释

> "我们的系统：Planner 阶段 LLM 无文件系统访问，但可以在计划中包含读取步骤"

## 简单理解

### 类比：餐厅点餐

**Claude Code（有文件系统访问）**：
- 就像在自助餐厅
- 你可以随时去拿任何食物（文件）
- 看到菜单（SKILL.md）说"还有甜点"，你可以立即去拿

**我们的系统（计划式）**：
- 就像在普通餐厅
- 你不能自己去厨房拿食物
- 但你可以看菜单（SKILL.md），看到"还有甜点"
- 你可以在点餐时（生成计划）说："我要一份甜点"
- 服务员（Executor）会帮你拿过来

## 具体工作流程

### 场景：使用 skill-creator 创建新 skill

#### 步骤 1：路由阶段
```
用户: "我想创建一个新的skill"
↓
系统: 匹配到 skill-creator
```

#### 步骤 2：加载技能内容（渐进式加载）

**系统只加载 SKILL.md**（17,701 字符）：
```markdown
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

**注意**：
- ✅ LLM 看到了 SKILL.md 的完整内容
- ✅ LLM 看到了提示："See references/workflows.md"
- ❌ 但 LLM **看不到** workflows.md 的实际内容（因为还没读取）

#### 步骤 3：LLM 生成计划

**LLM 的思考过程**：
1. 看到任务："创建新 skill"
2. 看到 SKILL.md 说："See references/workflows.md"
3. 决定："我需要看 workflows.md 来了解工作流模式"
4. 在计划中添加一个步骤："读取 workflows.md"

**LLM 生成的计划**：
```json
{
  "steps": [
    {
      "step_id": "step_1",
      "tool_id": "file",
      "description": "读取 workflows.md 了解工作流模式",
      "params": {
        "operation": "read",
        "path": "skills_workspace/skill-creator/references/workflows.md"
      },
      "risk_level": "R1"
    },
    {
      "step_id": "step_2",
      "tool_id": "file",
      "description": "创建新 skill 的 SKILL.md 文件",
      "params": {
        "operation": "write",
        "path": "skills_workspace/my-new-skill/SKILL.md",
        "content": "# My New Skill\n\n..."
      },
      "risk_level": "R1"
    }
  ]
}
```

#### 步骤 4：执行阶段

**Executor 执行步骤 1**：
```python
# 调用 FileTool
result = file_tool.execute({
    "operation": "read",
    "path": "skills_workspace/skill-creator/references/workflows.md"
})

# 返回：
# {
#   "content": "# Workflow Patterns\n\n## Sequential Workflows\n...",
#   "path": "/path/to/workflows.md"
# }
```

**现在**：
- ✅ workflows.md 的内容已经被读取
- ✅ 可以用于后续步骤（如步骤 2 创建新文件时参考）

## 关键点

### 1. Planner 阶段 LLM 的状态

**LLM 能看到**：
- ✅ 任务描述
- ✅ SKILL.md 的完整内容
- ✅ 可用工具列表（包括 file 工具）

**LLM 不能做**：
- ❌ 不能直接读取文件系统中的文件
- ❌ 不能执行代码
- ❌ 只能生成计划（JSON 结构）

### 2. 为什么 LLM 知道要读取文件？

因为 SKILL.md 中已经包含了提示：
```markdown
- **Multi-step processes**: See references/workflows.md for sequential workflows
```

LLM 看到这个提示后，理解到：
- 有一个文件叫 `references/workflows.md`
- 这个文件包含工作流模式的信息
- 如果任务需要了解工作流，应该读取这个文件

### 3. 计划中的读取步骤

LLM 在计划中添加：
```json
{
  "tool_id": "file",
  "params": {
    "operation": "read",
    "path": "skills_workspace/skill-creator/references/workflows.md"
  }
}
```

这表示："在执行时，请读取这个文件"

### 4. 执行阶段的实际读取

Executor 看到这个步骤后：
1. 识别 tool_id = "file"
2. 调用 FileTool
3. FileTool 执行 `operation: "read"`
4. 实际读取文件内容
5. 返回内容给后续步骤使用

## 与 Claude Code 的对比

### Claude Code（真正的按需加载）

```
Claude 看到: "See references/workflows.md"
↓
Claude 立即执行: cat references/workflows.md
↓
Claude 立即看到文件内容
↓
Claude 继续处理（基于文件内容）
```

**特点**：实时、灵活、Claude 自己控制

### 我们的系统（计划式按需加载）

```
LLM 看到: "See references/workflows.md"
↓
LLM 生成计划: 添加 "读取 workflows.md" 步骤
↓
计划生成完成
↓
执行阶段: Executor 执行 "读取 workflows.md" 步骤
↓
文件内容被读取
↓
后续步骤可以使用文件内容
```

**特点**：计划式、可预测、通过工具执行

## 优势

1. **可审计**：所有文件访问都记录在计划中
2. **可预测**：计划生成时就确定了要读取哪些文件
3. **安全性**：所有文件访问都通过工具，有安全检查
4. **符合架构**：计划-执行分离，符合系统设计

## 总结

**"Planner 阶段 LLM 无文件系统访问，但可以在计划中包含读取步骤"** 的意思是：

- **Planner 阶段**：LLM 只是一个 API，不能直接操作文件系统
- **但 LLM 很智能**：看到 SKILL.md 中的引用提示后，知道需要读取这些文件
- **生成计划时**：LLM 在计划中"声明"需要读取的文件（通过 file.read 步骤）
- **执行阶段**：Executor 通过 FileTool 实际读取文件
- **结果**：实现了"按需加载"的效果，虽然方式不同，但功能完整

这种方式虽然不如 Claude Code 的直接文件访问灵活，但在我们的架构中是合理的，因为：
- 保持了计划的可预测性和可审计性
- 所有操作都通过工具，便于安全控制
- 符合计划-执行分离的架构设计
