from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class MemoryNote:
    id: Optional[str]
    text: str
    ts: Optional[float] = None
    source: str = "jarvis"
    tags: Optional[List[str]] = None

@dataclass
class SearchResult:
    id: str
    text: str
    score: float
    ts: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None

