"""
消息分类模块：判断用户输入是否需要写入记忆库

根据用户输入的文本特征，将其分类为：
- EXPLICIT_STORE: 显式要求记录（如"为了记录：""帮我记一下"）
- NEVER_STORE: 明显不需要记录（如 debug 命令、一次性问句）
- CANDIDATE: 不确定，交给 LLM 判断
"""
from __future__ import annotations
from enum import Enum
from typing import List
import re

class MemoryStoreDecision(Enum):
    """记忆存储决策"""
    EXPLICIT_STORE = "explicit_store"  # 显式要求记录
    NEVER_STORE = "never_store"        # 明确不记录
    CANDIDATE = "candidate"             # 由 LLM 判断


def classify_message_for_memory(text: str) -> MemoryStoreDecision:
    """
    根据用户输入判断其记忆策略
    
    Args:
        text: 用户输入的文本
        
    Returns:
        MemoryStoreDecision: 记忆存储决策
        
    规则说明：
    - EXPLICIT_STORE: 显式要求记录
      * 前缀匹配："为了记录："/"为了记录,"/"为了记录，"
      * "帮我记一下"/"帮我记住"/"记一下"/"记住这个"
      * 包含"以后要记住""你要记住"等长期记忆表达，且不是问句
      
    - NEVER_STORE: 明显不需要记录
      * 包含 debug/命令关键词："print("/"console.log"/"pip install"/"conda "/"git "/"curl " 等
      * 纯问句（以 ?/？ 结尾），且不包含"以后""今后""从现在开始""以后记住"等
      
    - 其它 → CANDIDATE: 不确定，由 LLM 判断
    
    示例：
        >>> classify_message_for_memory("为了记录：我住在26楼")
        <MemoryStoreDecision.EXPLICIT_STORE: 'explicit_store'>
        
        >>> classify_message_for_memory("print('hello')")
        <MemoryStoreDecision.NEVER_STORE: 'never_store'>
        
        >>> classify_message_for_memory("今天天气怎么样？")
        <MemoryStoreDecision.NEVER_STORE: 'never_store'>
        
        >>> classify_message_for_memory("我喜欢手冲咖啡")
        <MemoryStoreDecision.CANDIDATE: 'candidate'>
    """
    if not text or not text.strip():
        return MemoryStoreDecision.CANDIDATE
    
    text = text.strip()
    text_lower = text.lower()
    
    # 1. 检查 EXPLICIT_STORE 规则
    # 前缀匹配（忽略前导空格）
    explicit_prefixes = [
        "为了记录：", "为了记录,", "为了记录，",
        "帮我记一下", "帮我记住", "记一下", "记住这个"
    ]
    for prefix in explicit_prefixes:
        if text.startswith(prefix) or text_lower.startswith(prefix.lower()):
            return MemoryStoreDecision.EXPLICIT_STORE
    
    # 包含长期记忆表达，且不是问句
    long_term_patterns = [
        r"以后要记住", r"你要记住", r"以后记住", r"今后记住",
        r"从现在开始", r"以后要", r"今后要"
    ]
    is_question = text.endswith("?") or text.endswith("？")
    for pattern in long_term_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            if not is_question:
                return MemoryStoreDecision.EXPLICIT_STORE
    
    # 2. 检查 NEVER_STORE 规则
    # Debug/命令关键词
    debug_keywords = [
        "print(", "console.log", "pip install", "conda ", "git ", "curl ",
        "npm ", "yarn ", "docker ", "kubectl ", "ssh ", "sudo ",
        "import ", "from ", "def ", "class ", "if __name__"
    ]
    for keyword in debug_keywords:
        if keyword in text:
            return MemoryStoreDecision.NEVER_STORE
    
    # 纯问句（以 ?/？ 结尾），且不包含长期记忆表达
    if is_question:
        has_long_term = any(re.search(p, text, re.IGNORECASE) for p in long_term_patterns)
        if not has_long_term:
            return MemoryStoreDecision.NEVER_STORE
    
    # 3. 其它情况 → CANDIDATE
    return MemoryStoreDecision.CANDIDATE

