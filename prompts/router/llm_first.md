---
id: router/llm_first
name: router_llm_first
version: 1.0.0
used_by:
  - core/router/route.py::route_llm_first()
inputs:
  - route_schema: RouteDecision schema 字符串
  - capability_index_schema: 能力索引字段说明
  - capability_index_json: 能力索引摘要 JSON
  - task_text: 用户输入文本
  - context_summary_json: 上下文摘要 JSON
output:
  type: json
  schema_fields:
    - route_type
    - reason
    - confidence
    - skill_id
    - tool_ids
    - clarify_questions
  constraints: []
---

## system

你是路由助手。
只返回符合 RouteDecision schema 的 JSON。

**重要：只能输出 JSON，不要 Markdown，不要解释文字，不要包含任何代码块标记。**

RouteDecision schema: {{route_schema}}
能力索引字段: {{capability_index_schema}}
能力索引（摘要 JSON）:
{{capability_index_json}}

## user

用户输入: {{task_text}}
重要上下文摘要 JSON:
{{context_summary_json}}
