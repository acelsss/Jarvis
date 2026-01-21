"""File system utilities."""
from pathlib import Path
from typing import Optional


def ensure_dir(path: str) -> Path:
    """确保目录存在。
    
    Args:
        path: 目录路径
        
    Returns:
        Path对象
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def safe_path(base: str, *parts: str) -> Path:
    """安全地构建路径（防止路径遍历）。
    
    Args:
        base: 基础路径
        *parts: 路径部分
        
    Returns:
        安全路径
    """
    # TODO: 实现路径安全检查
    return Path(base, *parts)
