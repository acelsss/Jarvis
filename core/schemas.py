from dataclasses import dataclass
from typing import Optional, Literal, Dict, Any

Intent = Literal["store", "recall", "task", "passthrough"]

@dataclass
class Request:
    text: str
    source: str = "cli"
    ts: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None

@dataclass
class Response:
    ok: bool
    intent: Intent
    msg: str
    data: Optional[Dict[str, Any]] = None

