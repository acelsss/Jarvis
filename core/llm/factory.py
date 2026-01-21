"""Factory for pluggable LLM clients."""

from __future__ import annotations

import os
from typing import Optional

from .client_base import LLMClient


class OpenAIClient(LLMClient):
    """Placeholder OpenAI client."""

    def complete_json(
        self, purpose: str, system: str, user: str, schema_hint: str
    ) -> dict:
        raise NotImplementedError("OpenAI client is not implemented yet.")


class GeminiClient(LLMClient):
    """Placeholder Gemini client."""

    def complete_json(
        self, purpose: str, system: str, user: str, schema_hint: str
    ) -> dict:
        raise NotImplementedError("Gemini client is not implemented yet.")


def build_llm_client() -> Optional[LLMClient]:
    provider = os.getenv("LLM_PROVIDER")
    if not provider:
        return None

    provider = provider.strip().lower()
    if provider in ("", "none"):
        return None
    if provider == "openai":
        return OpenAIClient()
    if provider == "gemini":
        return GeminiClient()

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
