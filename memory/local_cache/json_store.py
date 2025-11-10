import json
from pathlib import Path
from typing import List, Dict, Any
from utils.logger import get_logger

log = get_logger(__name__)
DB = Path("memory/local_cache/cache.json")

def _load() -> Dict[str, Any]:
    if not DB.exists():
        return {"notes": []}
    return json.loads(DB.read_text(encoding="utf-8"))

def _save(obj: Dict[str, Any]):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def add_note(text: str, source: str = "jarvis"):
    obj = _load()
    obj["notes"].append({"text": text, "source": source})
    _save(obj)
    return True

def search(query: str, top_k: int = 5):
    obj = _load()
    notes = obj.get("notes", [])
    # 朴素关键词包含
    matched = [ {"text": n["text"], "score": 1.0} for n in notes if query in n["text"] ]
    return matched[:top_k]

