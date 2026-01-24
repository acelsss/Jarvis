"""Base LLM client interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class LLMClient(ABC):
    """Abstract LLM client."""

    @abstractmethod
    def complete_json(
        self, 
        purpose: str, 
        system: str, 
        user: str, 
        schema_hint: str,
        chat_history_messages: Optional[List[Dict[str, str]]] = None,
    ) -> Dict:
        """Return structured JSON output as a dict.
        
        Args:
            purpose: 调用目的
            system: 系统提示词
            user: 用户提示词
            schema_hint: JSON schema 提示
            chat_history_messages: 可选的对话历史消息列表，格式为 [{"role": "user|assistant", "content": "..."}]
        
        Returns:
            结构化的 JSON 输出字典
        """
        raise NotImplementedError
