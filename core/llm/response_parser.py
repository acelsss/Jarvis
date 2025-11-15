"""
LLM 返回解析模块

解析 DeepSeek 返回的 JSON 字符串，提取 reply 和 memories_to_store
包含防御性解析，确保异常情况下不会中断主流程
"""
from __future__ import annotations
import json
import re
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
from utils.logger import get_logger

log = get_logger(__name__)


@dataclass
class LLMMemoryItem:
    """LLM 返回的记忆项（内部数据结构）"""
    content: str
    tags: List[str]
    metadata: Dict[str, Any]


def parse_deepseek_response(raw: str) -> Tuple[str, List[LLMMemoryItem]]:
    """
    解析 DeepSeek 返回的 JSON 字符串
    
    Args:
        raw: LLM 返回的原始文本
        
    Returns:
        (reply, memories_to_store_list) 元组
        
    防御性解析：
    - json.loads 失败 → 降级为：reply=原始文本，memories_to_store=[]
    - memories_to_store 不是数组 → 当作空数组
    - content 为空或超长（> 2000 字符） → 丢弃该条
    """
    if not raw or not raw.strip():
        log.warning("[Jarvis][llm] Empty response from LLM")
        return "", []
    
    raw = raw.strip()
    
    # 尝试提取 JSON（可能包含 markdown 代码块）
    json_str = raw
    
    # 如果包含 ```json 或 ``` 代码块，提取其中的 JSON
    json_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
    if json_block_match:
        json_str = json_block_match.group(1)
    else:
        # 尝试直接提取第一个 {...} 块
        brace_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if brace_match:
            json_str = brace_match.group(0)
    
    try:
        data = json.loads(json_str)
        
        # 提取 reply
        reply = data.get("reply", "")
        if not reply:
            # 如果没有 reply 字段，尝试使用原始文本
            reply = raw
        
        # 提取 memories_to_store
        memories_raw = data.get("memories_to_store", [])
        if not isinstance(memories_raw, list):
            log.warning(f"[Jarvis][llm] memories_to_store is not a list: {type(memories_raw)}")
            memories_raw = []
        
        # 验证并转换每条记忆
        memories = []
        for idx, mem_raw in enumerate(memories_raw):
            if not isinstance(mem_raw, dict):
                log.warning(f"[Jarvis][llm] Memory item {idx} is not a dict, skipping")
                continue
            
            content = mem_raw.get("content", "").strip()
            if not content:
                log.warning(f"[Jarvis][llm] Memory item {idx} has empty content, skipping")
                continue
            
            # 长度限制（> 2000 字符则丢弃）
            if len(content) > 2000:
                log.warning(f"[Jarvis][llm] Memory item {idx} content too long ({len(content)} chars), skipping")
                continue
            
            # 提取 tags
            tags_raw = mem_raw.get("tags", [])
            if not isinstance(tags_raw, list):
                tags = []
            else:
                tags = [str(t).strip() for t in tags_raw if t and str(t).strip()]
            
            # 提取 metadata
            metadata_raw = mem_raw.get("metadata", {})
            if not isinstance(metadata_raw, dict):
                metadata = {}
            else:
                metadata = {k: v for k, v in metadata_raw.items() if v is not None}
            
            memories.append(LLMMemoryItem(
                content=content,
                tags=tags,
                metadata=metadata
            ))
        
        log.info(f"[Jarvis][llm] Parsed response: reply_len={len(reply)}, memories_count={len(memories)}")
        return reply, memories
    
    except json.JSONDecodeError as e:
        log.warning(f"[Jarvis][llm] Failed to parse JSON response: {e}")
        log.debug(f"[Jarvis][llm] Raw response (first 500 chars): {raw[:500]}")
        # 降级：返回原始文本作为 reply，memories 为空
        return raw, []
    
    except Exception as e:
        log.error(f"[Jarvis][llm] Unexpected error parsing response: {type(e).__name__}: {e}")
        # 降级：返回原始文本作为 reply，memories 为空
        return raw, []

