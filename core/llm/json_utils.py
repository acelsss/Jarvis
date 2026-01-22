"""JSON utilities for LLM outputs."""

from __future__ import annotations

import json
from typing import Optional


def _extract_outer_object(text: str) -> Optional[str]:
    start = text.find("{")
    if start == -1:
        return None
    end = text.rfind("}")
    if end == -1 or end <= start:
        return None
    return text[start : end + 1]


def _extract_from_markdown_code_block(text: str) -> Optional[str]:
    """尝试从 markdown 代码块中提取 JSON。"""
    import re
    # 匹配 ```json ... ``` 或 ``` ... ```
    patterns = [
        r'```json\s*\n(.*?)\n```',
        r'```\s*\n(.*?)\n```',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return None


def safe_load_json(text: str) -> dict:
    """Parse JSON, with a conservative outer-object fallback."""
    # 首先尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 尝试从 markdown 代码块中提取
    markdown_json = _extract_from_markdown_code_block(text)
    if markdown_json:
        try:
            return json.loads(markdown_json)
        except json.JSONDecodeError:
            pass

    # 尝试提取最外层的 JSON 对象
    candidate = _extract_outer_object(text)
    if not candidate:
        raise ValueError(f"Unable to parse JSON from text. First 200 chars: {text[:200]}")

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Unable to parse JSON from extracted object. Error: {exc}. Extracted: {candidate[:200]}") from exc
