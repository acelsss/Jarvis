"""OpenAI-compatible LLM provider."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

from ..client_base import LLMClient
from ..json_utils import safe_load_json

DEFAULT_BASE_URL = "https://api.openai.com"
DEFAULT_MODEL = "gpt-4.1-mini"
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


class OpenAICompatibleClient(LLMClient):
    """OpenAI-compatible client using Chat Completions."""

    def complete_json(
        self, purpose: str, system: str, user: str, schema_hint: str
    ) -> dict:
        api_key = _get_env_value("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider.")

        base_url = _get_env_value("OPENAI_BASE_URL", DEFAULT_BASE_URL)
        model = _get_env_value("OPENAI_MODEL", DEFAULT_MODEL)
        timeout_seconds = _get_timeout_seconds()

        system_content = "\n".join(
            [
                "You are a JSON-only assistant.",
                "Output ONLY a valid JSON object, no markdown or extra text.",
                f"Purpose: {purpose}",
                f"System instructions: {system}",
                f"Schema hint: {schema_hint}",
            ]
        )
        user_content = "\n".join(
            [
                user,
                "Reminder: output ONLY JSON.",
            ]
        )

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.2,
        }

        url = f"{base_url.rstrip('/')}/v1/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                response_text = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"OpenAI-compatible request failed with status {exc.code}."
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("OpenAI-compatible request failed to reach server.") from exc

        try:
            response_json = json.loads(response_text)
        except json.JSONDecodeError as exc:
            raise ValueError("OpenAI-compatible response is not valid JSON.") from exc

        try:
            content = response_json["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("OpenAI-compatible response missing message content.") from exc

        if not isinstance(content, str):
            raise ValueError("OpenAI-compatible message content is not a string.")

        return safe_load_json(content)


if __name__ == "__main__":
    fake_response = {
        "choices": [
            {
                "message": {
                    "content": "{\"ok\": true, \"source\": \"demo\"}"
                }
            }
        ]
    }
    parsed = safe_load_json(fake_response["choices"][0]["message"]["content"])
    print(parsed)
