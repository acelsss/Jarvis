# Route Contract v0.2

本文档定义 LLM-first 路由的稳定合同（RouteDecision），作为内核 API 的一部分。所有路由决策必须符合此 JSON 结构，且兼容性优先。

---

## 1. RouteDecision JSON Schema

### 1.1 必须字段

- `route_type`：路由类型枚举，必填
  - 允许值：`qa` | `skill` | `tool` | `mcp` | `clarify`
- `reason`：简要理由，必填

### 1.2 可选字段

- `confidence`：置信度，数值范围 `0.0 ~ 1.0`
- `skill_id`：当 `route_type = "skill"` 时必填
- `tool_ids`：当 `route_type = "tool"` 或 `route_type = "mcp"` 时必填
- `clarify_questions`：当 `route_type = "clarify"` 时必填（问题数组）

### 1.3 结构示意（JSON）

```json
{
  "route_type": "qa | skill | tool | mcp | clarify",
  "reason": "string",
  "confidence": 0.0,
  "skill_id": "string",
  "tool_ids": ["string"],
  "clarify_questions": ["string"]
}
```

---

## 2. Progressive Disclosure（能力渐进披露）

- Router 启动阶段**只提供 capability index**（能力索引）。
- LLM 只能基于索引字段完成“路由选择”。
- **仅在 `route_type = "skill"` 且选中 skill 之后**，才允许加载完整 `SKILL.md` 内容进入上下文。

能力索引字段建议：
`id` / `name` / `type`（skill|tool|mcp）/ `tags` / `description`（短摘要）。

---

## 3. 安全与风险裁决

- **Hard Guard（硬规则）优先级最高**：高风险动词/意图命中时，必须覆盖 LLM 判断。
- **风险下限由内核裁决**：LLM 只能建议，不能降低内核判定的风险级别。

---

## 4. RouteDecision 示例

### 示例 A：QA

```json
{
  "route_type": "qa",
  "reason": "用户请求解释概念，不需要执行工具或技能。",
  "confidence": 0.82
}
```

### 示例 B：Skill

```json
{
  "route_type": "skill",
  "reason": "任务与已注册技能高度匹配。",
  "confidence": 0.76,
  "skill_id": "skill.publish_blog"
}
```

### 示例 C：MCP/Tool + Clarify

```json
[
  {
    "route_type": "mcp",
    "reason": "需要远程浏览器能力完成任务。",
    "confidence": 0.71,
    "tool_ids": ["mcp.browser.navigate", "mcp.browser.capture"]
  },
  {
    "route_type": "clarify",
    "reason": "缺少必要参数，无法确定执行目标。",
    "confidence": 0.6,
    "clarify_questions": [
      "需要访问的具体网址是什么？",
      "是否允许登录账户？"
    ]
  }
]
```
