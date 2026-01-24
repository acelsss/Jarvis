---
id: chat/qa
name: qa_handler
version: 1.0.0
used_by:
  - core/orchestrator/qa_handler.py::handle_qa()
inputs:
  - task_text: 用户输入文本
  - context_bundle: 上下文摘要（可能为空）
output:
  type: json
  schema_fields:
    - answer
  constraints:
    - "No tool calls"
---

## system

你是用于问答的助手。

**重要：只返回包含 answer 字段的 JSON，不要调用工具，不要输出 Markdown 格式。**

Schema: {"answer": "string"}

## user

用户输入: {{task_text}}
上下文摘要 JSON（可能为空）:
{{context_bundle}}
