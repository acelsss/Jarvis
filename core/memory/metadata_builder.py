"""
记忆元数据构建模块

将 LLM 提供的 tags/metadata 与 Jarvis 的系统级信息合并
"""
from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone


def build_final_tags_and_metadata(
    llm_tags: Optional[List[str]],
    llm_metadata: Optional[Dict[str, Any]],
    user_id: str,
    channel: str,
    autolog: bool,
) -> tuple[List[str], Dict[str, Any]]:
    """
    将 LLM 提供的 tags/metadata 与 Jarvis 的系统级信息合并
    
    Args:
        llm_tags: LLM 提供的标签列表（可能为 None）
        llm_metadata: LLM 提供的元数据字典（可能为 None）
        user_id: 用户 ID
        channel: 渠道名称（如 "repl", "cli" 等）
        autolog: 是否为自动记录（True=LLM 自动提炼，False=用户显式要求）
        
    Returns:
        (final_tags, final_metadata) 元组
        
    系统级 tag:
    - "jarvis": 标识来自 Jarvis
    - f"user:{user_id}": 用户标识
    - f"channel:{channel}": 渠道标识
    
    系统级 metadata:
    - "source": 来源（如 "jarvis_repl"）
    - "autolog": 是否自动记录
    - "recorded_at": 记录时间（ISO 字符串）
    
    LLM 提供的 tags 与系统 tag 取并集（去重）
    LLM 提供的 metadata 覆盖系统默认值
    """
    # 1. 构建系统级 tags
    system_tags = ["jarvis", f"user:{user_id}", f"channel:{channel}"]
    
    # 2. 合并 tags（去重）
    final_tags = list(set(system_tags))
    if llm_tags:
        for tag in llm_tags:
            tag_str = str(tag).strip()
            if tag_str and tag_str not in final_tags:
                final_tags.append(tag_str)
    
    # 3. 构建系统级 metadata
    system_metadata = {
        "source": f"jarvis_{channel}",
        "autolog": autolog,
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds")
    }
    
    # 4. 合并 metadata（LLM 提供的覆盖系统默认值）
    final_metadata = system_metadata.copy()
    if llm_metadata:
        for k, v in llm_metadata.items():
            if v is not None:  # 只保留非 None 值
                final_metadata[k] = v
    
    return final_tags, final_metadata

