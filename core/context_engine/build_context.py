"""Context building logic."""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from core.contracts.task import Task
from core.platform.config import Config


def load_identity_pack(config_dir: str = "./identity_pack") -> Dict[str, Any]:
    """加载身份配置包。
    
    Args:
        config_dir: 配置目录路径
        
    Returns:
        身份配置字典
    """
    config = Config(config_dir)
    identity = {
        "constitution": config.load_yaml("constitution.yaml"),
        "preferences": config.load_yaml("preferences.yaml"),
        "voice_style": config.load_yaml("voice_style.yaml"),
        "skills_profile": config.load_yaml("skills_profile.yaml"),
        "memory_policy": config.load_yaml("memory_policy.yaml"),
    }
    return identity


async def search_openmemory(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """搜索 OpenMemory（stub实现）。
    
    Args:
        query: 查询字符串
        top_k: 返回结果数量
        
    Returns:
        记忆结果列表
    """
    # TODO: 实现真实的 OpenMemory 搜索
    # v0.1: 返回空结果
    return []


def build_context(
    task: Task,
    identity_pack: Optional[Dict[str, Any]] = None,
    openmemory_results: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """构建任务上下文。
    
    Args:
        task: 任务对象
        identity_pack: 身份配置包（如果为None则自动加载）
        openmemory_results: OpenMemory 搜索结果
        
    Returns:
        上下文字典
    """
    if identity_pack is None:
        identity_pack = load_identity_pack()
    
    context = {
        "task_id": task.task_id,
        "description": task.description,
        "status": task.status,
        "task_context": task.context,
        "identity": identity_pack,
        "openmemory": openmemory_results or [],
    }
    
    return context
