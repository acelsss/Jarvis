"""ID generation utilities."""
import uuid
from typing import Optional


def generate_id(prefix: Optional[str] = None) -> str:
    """生成唯一ID。
    
    Args:
        prefix: ID前缀
        
    Returns:
        唯一ID字符串
    """
    id_str = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{id_str}"
    return id_str
