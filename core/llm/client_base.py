"""Base LLM client interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict


class LLMClient(ABC):
    """Abstract LLM client."""

    @abstractmethod
    def complete_json(
        self, purpose: str, system: str, user: str, schema_hint: str
    ) -> Dict:
        """Return structured JSON output as a dict."""
        raise NotImplementedError
