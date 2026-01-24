"""Session history buffer for maintaining short-term conversation context."""
import os
from typing import List, Dict, Optional


class SessionHistoryBuffer:
    """短期对话历史缓冲区，使用滑动窗口机制。
    
    数据结构：messages: list[dict]，格式兼容 OpenAI messages：
    {"role": "user|assistant|system", "content": "..."}
    """
    
    def __init__(self, max_turns: Optional[int] = None):
        """初始化历史缓冲区。
        
        Args:
            max_turns: 最大轮数（一轮 = user + assistant），默认从环境变量读取
        """
        if max_turns is None:
            max_turns = int(os.getenv("CHAT_HISTORY_MAX_TURNS", "12"))
        self.max_turns = max_turns
        self.messages: List[Dict[str, str]] = []
    
    def add_user(self, text: str) -> None:
        """添加用户消息。
        
        Args:
            text: 用户输入文本
        """
        if not text or not text.strip():
            return
        self.messages.append({
            "role": "user",
            "content": text.strip()
        })
    
    def add_assistant(self, text: str) -> None:
        """添加助手回复。
        
        Args:
            text: 助手回复文本
        """
        if not text or not text.strip():
            return
        self.messages.append({
            "role": "assistant",
            "content": text.strip()
        })
    
    def get_window(self, max_turns: Optional[int] = None) -> List[Dict[str, str]]:
        """获取滑动窗口内的历史消息。
        
        Args:
            max_turns: 最大轮数，如果为 None 则使用实例的 max_turns
        
        Returns:
            最近 N 轮对话对应的消息列表（最多 2N 条消息）
        """
        if max_turns is None:
            max_turns = self.max_turns
        
        if max_turns <= 0:
            return []
        
        # 计算需要保留的消息数量（每轮 = user + assistant = 2 条消息）
        max_messages = max_turns * 2
        
        if len(self.messages) <= max_messages:
            return self.messages.copy()
        
        # 只返回最后 N 轮的消息
        return self.messages[-max_messages:].copy()
    
    def reset(self) -> None:
        """清空历史记录。"""
        self.messages.clear()
    
    def __len__(self) -> int:
        """返回消息数量。"""
        return len(self.messages)
