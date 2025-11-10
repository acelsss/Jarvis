import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from core.schemas import Request, Response

DB = Path("memory/local_tasks.json")

def _load() -> List[Dict[str, Any]]:
    if not DB.exists():
        return []
    return json.loads(DB.read_text(encoding="utf-8"))

def _save(items: List[Dict[str, Any]]):
    DB.parent.mkdir(parents=True, exist_ok=True)
    DB.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

def run(req: Request, mem=None) -> dict:
    meta = req.meta or {}
    op = meta.get("op", "add")

    if op == "add":
        items = _load()
        item = {
            "id": f"T{len(items)+1:03d}",
            "title": meta.get("title") or req.text,
            "status": "open",
            "created_at": datetime.now().isoformat(timespec="seconds")
        }
        items.append(item)
        _save(items)
        return Response(ok=True, intent="task", msg=f"📋 已添加任务（{item['id']}）", data=item).__dict__

    if op == "list":
        items = _load()
        return Response(ok=True, intent="task", msg=f"🗒️ 共 {len(items)} 条任务", data={"items": items}).__dict__

    if op == "done":
        items = _load()
        ident = meta.get("id", "").strip()
        for it in items:
            if it["id"] == ident:
                it["status"] = "done"
                it["done_at"] = datetime.now().isoformat(timespec="seconds")
                _save(items)
                return Response(ok=True, intent="task", msg=f"✅ 已完成 {ident}", data=it).__dict__
        return Response(ok=False, intent="task", msg=f"未找到任务 {ident}").__dict__

    return Response(ok=False, intent="task", msg="未支持的任务操作").__dict__

