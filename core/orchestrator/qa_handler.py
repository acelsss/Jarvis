"""QA handler for chat responses."""
import os
from typing import Any, Optional


def _truncate_text(text: str, max_len: int = 200) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _get_llm_model(provider: str) -> Optional[str]:
    provider = provider.strip().lower()
    if provider == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    return None


def _log_llm_qa(audit_logger: Any, provider: str, answer: str) -> None:
    if not audit_logger:
        return
    details = {
        "provider": provider,
        "model": _get_llm_model(provider),
        "answer_len": len(answer or ""),
        "answer_excerpt": _truncate_text(answer or "", max_len=200),
    }
    audit_logger.log("llm.qa", details)


def handle_qa(
    task_text: str,
    context_bundle: Any,
    llm_client: Any,
    audit_logger: Any = None,
) -> str:
    """处理 QA 路由，返回回答文本。"""
    if not llm_client:
        return "LLM 不可用，无法生成回答。"

    provider = os.getenv("LLM_PROVIDER", "unknown")
    system = "\n".join(
        [
            "你是用于问答的助手。",
            "只返回包含 answer 字段的 JSON。",
            "Schema: {\"answer\": \"string\"}",
        ]
    )
    user = "\n".join(
        [
            f"用户输入: {task_text}",
            "上下文摘要 JSON（可能为空）:",
            str(context_bundle) if context_bundle is not None else "{}",
        ]
    )
    result = llm_client.complete_json(
        purpose="qa",
        system=system,
        user=user,
        schema_hint='{"answer":"string"}',
    )
    answer = ""
    if isinstance(result, dict):
        answer = result.get("answer") or ""
    if not answer:
        answer = "对不起，我没有生成有效回答。"

    _log_llm_qa(audit_logger, provider, answer)
    return answer
