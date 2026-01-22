# Skill-Creator 流程分析

## 用户问题梳理

用户想确认：
1. 流程理解是否正确
2. 是否符合官方 skill-creator 设计
3. Jarvis 实际运行是否符合这个流程
4. LLM 是否会通过 Jarvis 询问问题

---

## 理想流程（官方设计）

### 阶段 1：路由（Routing）
```
用户输入: "我想创建一个新的 xxx 技能"
↓
Jarvis 路由 → 匹配到 skill-creator
```

### 阶段 2：加载技能内容（渐进式加载）
```
1. 只加载 SKILL.md（不包含引用文件）
2. SKILL.md 中包含提示，如：
   - "查看 references/workflows.md 了解工作流模式"
   - "查看 references/output-patterns.md 了解输出模式"
```

### 阶段 3：计划生成（Planning）
```
LLM 看到：
- ✅ SKILL.md 的完整内容
- ✅ 提示："See references/workflows.md"
- ❌ 但看不到 workflows.md 的实际内容

LLM 生成计划：
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
      "description": "创建新技能的 SKILL.md",
      "params": {
        "operation": "write",
        "path": "skills_workspace/new-skill/SKILL.md",
        "content": "..."
      }
    }
  ]
}
```

### 阶段 4：执行（Execution）
```
Executor 执行计划：
1. 步骤1：读取 workflows.md → 返回文件内容
2. 步骤2：使用读取的内容 + SKILL.md 指导 → 创建新技能文件
```

### 阶段 5：询问问题（如果需要）
```
如果 LLM 需要更多信息，可以通过以下方式：
1. 路由阶段返回 "clarify" → 显示问题给用户
2. 执行阶段：目前没有机制让 LLM 在执行过程中询问问题
```

---

## Jarvis 实际实现

### ✅ 已实现的部分

#### 1. 路由阶段
- **位置**: `core/router/route.py::route_llm_first()`
- **功能**: 
  - ✅ 可以路由到 skill-creator
  - ✅ 可以返回 "clarify" 类型，显示问题给用户
- **代码**:
```python
elif route_type == "clarify":
    print("\n需要澄清，不进入规划与执行。")
    questions = route_decision.get("clarify_questions") or []
    if questions:
        print("澄清问题：")
        for q in questions:
            print(f"- {q}")
    return
```

#### 2. 渐进式加载
- **位置**: `skills/registry.py::load_skill_fulltext()`
- **功能**:
  - ✅ 默认只加载 SKILL.md（`include_references=False`）
  - ✅ SKILL.md 中包含引用提示
- **代码**:
```python
def _load_skill_fulltext(skill_id: str) -> str:
    # 根据渐进式加载原则：只加载 SKILL.md，不自动加载引用文件
    fulltext = skills_registry.load_skill_fulltext(skill_id, include_references=False)
    return fulltext
```

#### 3. 计划生成
- **位置**: `core/orchestrator/planner.py::create_plan()`
- **功能**:
  - ✅ LLM 看到 SKILL.md 内容
  - ✅ LLM 看到引用提示（如 "See references/workflows.md"）
  - ✅ LLM 可以生成包含 "file.read" 步骤的计划
- **系统提示**:
```python
"如果技能文档中提到了引用文件（如 references/workflows.md），
你可以在计划中添加 file.read 步骤来读取这些文件。"
```

#### 4. 执行阶段
- **位置**: `core/orchestrator/executor.py`
- **功能**:
  - ✅ 执行 file.read 步骤，读取引用文件
  - ✅ 执行 file.write 步骤，创建新技能文件
  - ❌ **但是**：目前没有机制让 LLM 在执行过程中询问问题

---

## 关键差异

### 官方设计 vs Jarvis 实现

| 方面 | 官方设计（Claude Code） | Jarvis 实现 |
|------|------------------------|------------|
| **文件访问** | Claude 有直接文件系统访问 | LLM 通过计划步骤访问文件 |
| **按需加载** | Claude 自己决定何时读取文件 | LLM 在计划中指定读取步骤 |
| **询问问题** | Claude 可以在执行过程中询问 | 只能在路由阶段询问（clarify） |

### 执行过程中的问题询问

**官方设计**：
- Claude Code 可以在执行过程中随时询问用户问题
- 用户回答后，Claude 继续执行

**Jarvis 当前实现**：
- ❌ **没有**执行过程中的问题询问机制
- ✅ 只能在路由阶段通过 "clarify" 类型询问问题
- ✅ 执行是"一次性"的，不会中途暂停询问

---

## 实际运行流程验证

### 测试案例：创建 code-reviewer 技能

#### 步骤 1：路由
```
用户输入: "我想创建一个新的技能，用于代码审查..."
↓
路由决策: {
  "route_type": "skill",
  "skill_id": "skill-creator",
  "confidence": 0.95
}
✅ 成功路由到 skill-creator
```

#### 步骤 2：加载技能内容
```
加载: skills_workspace/skill-creator/SKILL.md
大小: ~7.6K 字符（不包含引用文件）
✅ 符合渐进式加载原则
```

#### 步骤 3：计划生成
```
LLM 生成的计划:
{
  "steps": [
    {
      "tool_id": "file",
      "description": "读取代码审查检查清单 references/checklist.md",
      "params": {
        "operation": "read",
        "path": "references/checklist.md"  // ⚠️ 路径问题
      }
    },
    {
      "tool_id": "file",
      "description": "创建 code-reviewer 技能目录结构",
      "params": {
        "operation": "write",
        "path": "code-reviewer/SKILL.md",
        "content": "..."  // ✅ 完整内容
      }
    }
  ]
}
```

#### 步骤 4：执行
```
✅ 步骤1：读取引用文件（如果路径正确）
✅ 步骤2：创建新技能文件
❌ 但路径问题导致文件读取失败
```

---

## 总结

### ✅ 你的理解基本正确

1. **路由定位到 skill-creator** ✅
2. **加载 SKILL.md 内容发给 LLM** ✅
3. **LLM 反馈需要调用 reference 或 py 文件** ✅
4. **Jarvis 应该发给 LLM 相关 reference** ✅（通过计划步骤）

### ⚠️ 需要澄清的部分

1. **执行 py 脚本**：
   - ❌ 目前 **不能**直接执行 skill 文件夹中的 py 脚本
   - ✅ 只能通过 file.read 读取脚本内容
   - ⚠️ ShellTool 只允许 `echo` 命令，不能执行 `python3 script.py`

2. **询问问题**：
   - ✅ 路由阶段可以询问（通过 "clarify" 类型）
   - ❌ 执行过程中 **不能**询问问题
   - 这是与官方设计的主要差异

### 📋 是否符合官方设计？

| 方面 | 符合度 |
|------|--------|
| 渐进式加载 | ✅ 完全符合 |
| 按需读取引用文件 | ✅ 基本符合（通过计划步骤） |
| 执行过程中询问问题 | ❌ 不符合（只能在路由阶段询问） |
| 执行脚本 | ❌ 不符合（只能读取，不能执行） |

### 🔧 改进建议

1. **路径问题**：LLM 生成的路径需要相对于项目根目录或 sandbox_root
2. **执行脚本**：考虑允许执行 skill 文件夹中的脚本（需要安全机制）
3. **询问问题**：考虑在执行过程中支持 LLM 询问问题（需要交互机制）
