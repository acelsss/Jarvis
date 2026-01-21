"""Factory for pluggable LLM clients."""

from __future__ import annotations

import os
from typing import Optional

from .client_base import LLMClient
from .providers.gemini import GeminiClient
from .providers.openai_compat import OpenAICompatibleClient


def build_llm_client() -> Optional[LLMClient]:
    provider = os.getenv("LLM_PROVIDER")
    if not provider:
        return None

    provider = provider.strip().lower()
    if provider in ("", "none"):
        return None
    if provider == "openai":
        return OpenAICompatibleClient()
    if provider == "gemini":
        return GeminiClient()

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")
