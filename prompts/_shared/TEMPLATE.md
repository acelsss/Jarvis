---
id: category/prompt_name
name: prompt_human_readable_name
version: 1.0.0
used_by:
  - core/module/file.py::function_name()
inputs:
  - var_name: 变量描述（所有 {{var_name}} 必须在此声明）
  - another_var: 另一个变量的描述
output:
  type: json  # 或 text
  schema_fields:  # JSON 输出时必需字段（可选）
    - field1
    - field2
  constraints: []  # 额外约束（如 ["No tool calls"]）
model_hints:  # 可选：模型参数建议
  temperature: 0.7
  max_tokens: 2000
---

## system

你是 [角色描述]。
[系统指令和约束]

[可以使用 {{var_name}} 引用变量]

## user

[用户输入模板]

用户输入: {{another_var}}

[更多内容...]

## assistant

[可选：few-shot 示例，如果不需要可以删除此分段]

---

## 使用说明

### 对于 JSON 输出类型（router/planner）

```yaml
output:
  type: json
  schema_fields:
    - route_type
    - confidence
    - skill_id
```

### 对于文本输出类型（chat/qa）

```yaml
output:
  type: text
  constraints:
    - "No tool calls"
```

### 变量使用

- 所有变量必须用双大括号：`{{var_name}}`
- 所有变量必须在 frontmatter.inputs 中声明
- 变量名建议使用 snake_case

### Role 分段

- **必须包含** `## system` 分段
- **可选包含** `## user` 分段
- **可选包含** `## assistant` 分段（用于 few-shot 示例）
- 禁止使用 `---` 作为分隔符（与 YAML frontmatter 冲突）
