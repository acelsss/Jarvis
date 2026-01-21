"""Time utilities."""
from datetime import datetime
from typing import Optional


def now() -> datetime:
    """获取当前时间。"""
    return datetime.now()


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """格式化时间戳。"""
    if dt is None:
        dt = now()
    return dt.isoformat()
