"""Google Gemini API client using generateContent."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

from ..client_base import LLMClient
from ..json_utils import safe_load_json

DEFAULT_MODEL = "gemini-1.5-flash"
DEFAULT_TIMEOUT_SECONDS = 30


def _get_env_value(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def _get_timeout_seconds() -> int:
    raw = _get_env_value("LLM_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        return max(1, int(float(raw)))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


class GeminiClient(LLMClient):
    """Gemini client using REST generateContent."""

    def complete_json(
        self, purpose: str, system: str, user: str, schema_hint: str
    ) -> dict:
        api_key = _get_env_value("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required for Gemini provider.")

        model = _get_env_value("GEMINI_MODEL", DEFAULT_MODEL)
        timeout_seconds = _get_timeout_seconds()

        system_text = "\n".join(
            [
                "你是仅输出 JSON 的助手。",
                "只输出有效 JSON 对象，不要输出 Markdown 或额外文本。",
                f"目的: {purpose}",
                f"系统指令: {system}",
                f"Schema 提示: {schema_hint}",
            ]
        )
        user_text = "\n".join(
            [
                user,
                "提醒：只输出 JSON。",
            ]
        )

        payload = {
            "system_instruction": {"parts": [{"text": system_text}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": {"temperature": 0.2},
        }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "x-goog-api-key": api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                response_text = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"Gemini request failed with status {exc.code}."
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("Gemini request failed to reach server.") from exc

        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise ValueError("Gemini response is not valid JSON.") from exc

        try:
            parts = response_json["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Gemini response missing content parts.") from exc

        if not isinstance(parts, list):
            raise ValueError("Gemini response content parts is not a list.")

        texts = []
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                texts.append(part["text"])

        if not texts:
            raise ValueError("Gemini response content has no text parts.")

        return safe_load_json("".join(texts))


if __name__ == "__main__":
    fake_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "{\"ok\": true, \"source\": \"demo\"}"}
                    ]
                }
            }
        ]
    }
    text = "".join(part["text"] for part in fake_response["candidates"][0]["content"]["parts"])
    parsed = safe_load_json(text)
    print(parsed)
