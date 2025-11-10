from core.schemas import Response

def as_text(resp: Response) -> str:
    if not resp.ok:
        return f"❌ {resp.msg}"
    if resp.intent == "store":
        return "✅ 已记录到记忆库。"
    if resp.intent == "recall":
        items = resp.data.get("items", []) if resp.data else []
        if not items:
            return "🔍 没有找到相关记忆。"
        lines = [f"🔍 找到 {len(items)} 条："]
        for i, it in enumerate(items, 1):
            ts = it.get("time") or it.get("ts") or ""
            text = it.get("text") or it.get("content") or ""
            lines.append(f"{i}. [{ts}] {text}")
        return "\n".join(lines)
    if resp.intent == "task":
        return resp.msg or "📋 任务已更新。"
    return resp.msg or "✅ 已处理。"

