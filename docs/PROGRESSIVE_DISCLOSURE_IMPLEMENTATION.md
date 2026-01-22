# 渐进式加载实现说明

## Anthropic Agent Skills 渐进式加载原则

根据 [Anthropic 官方文档](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)，Agent Skills 使用三层渐进式加载：

### 第一层：Metadata（启动时）
- 只加载 `name` 和 `description`
- 用于路由决策
- 大小：~100 词

### 第二层：SKILL.md 完整内容（skill 触发时）
- 加载完整的 SKILL.md 文件
- 包含核心指令和工作流
- 大小：通常 <5k 词

### 第三层：引用文件（按需加载）
- **关键**：Claude 根据需要选择性地读取引用文件
- **不是**：系统自动加载所有引用文件
- Claude 看到 SKILL.md 中的提示（如 "See reference.md"）后，决定是否读取

## 当前实现

### ✅ 已符合标准的部分

1. **第一层（Metadata）**：
   - `scan_workspace(load_fulltext=False)` 只加载 frontmatter
   - 用于构建能力索引

2. **第二层（SKILL.md）**：
   - `load_skill_fulltext(skill_id, include_references=False)` 只加载主文件
   - 符合渐进式加载原则

### ⚠️ 需要理解的部分

**在 Claude Code 中**：
- Claude 有文件系统访问能力
- Claude 可以自己读取 `references/workflows.md` 等文件
- 这是真正的"按需加载"

**在我们的系统中**：
- Planner 阶段：LLM 没有文件系统访问能力
- 执行阶段：可以通过文件工具读取引用文件

**解决方案**：
- 计划生成时：只加载 SKILL.md（符合标准）
- SKILL.md 中已经包含引用提示（如 "See references/workflows.md"）
- LLM 看到这些提示后，可以在生成的计划中包含"读取引用文件"的步骤
- 执行阶段：通过文件工具读取引用文件

## 代码变更

### 修改 `load_skill_fulltext()` 默认行为

**之前**：
```python
load_skill_fulltext(skill_id, include_references=True)  # 默认加载所有引用
```

**现在**：
```python
load_skill_fulltext(skill_id, include_references=False)  # 默认只加载SKILL.md
```

**原因**：
- 符合 Anthropic 渐进式加载标准
- SKILL.md 中已经包含引用提示
- LLM 可以根据提示决定是否需要读取引用文件

### 使用场景

**场景1：计划生成（推荐）**
```python
# 只加载SKILL.md，符合渐进式加载
skill_fulltext = registry.load_skill_fulltext(skill_id, include_references=False)
```

**场景2：需要完整内容（向后兼容）**
```python
# 明确要求加载所有引用文件
skill_fulltext = registry.load_skill_fulltext(skill_id, include_references=True)
```

## 效果

### 之前（自动加载所有引用）
- skill-creator: 38,125 字符
- 导致超时问题

### 现在（只加载SKILL.md）
- skill-creator: 17,701 字符
- 减少 53% 的内容
- 避免超时问题
- 符合渐进式加载标准

## 验证

SKILL.md 中已经包含引用提示：
- Line 287: "See references/workflows.md for sequential workflows"
- Line 288: "See references/output-patterns.md for template and example patterns"

LLM 看到这些提示后：
1. 理解有这些引用文件可用
2. 在生成计划时，如果需要，可以包含"读取引用文件"的步骤
3. 执行阶段通过文件工具读取

## 总结

✅ **符合 Anthropic 标准**：
- 第一层：只加载 metadata
- 第二层：只加载 SKILL.md
- 第三层：LLM 根据需要决定是否读取引用文件

✅ **解决超时问题**：
- 内容减少 53%
- 避免 30 秒超时

✅ **保持灵活性**：
- 仍支持 `include_references=True` 向后兼容
- LLM 可以根据 SKILL.md 中的提示决定是否需要引用文件
