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


def safe_load_json(text: str) -> dict:
    """Parse JSON, with a conservative outer-object fallback."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    candidate = _extract_outer_object(text)
    if not candidate:
        raise ValueError("Unable to parse JSON from text.")

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError("Unable to parse JSON from extracted object.") from exc
