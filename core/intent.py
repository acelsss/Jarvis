import re
from typing import Tuple, Dict, Any
from core.schemas import Intent

def detect_intent(text: str) -> Tuple[Intent, Dict[str, Any]]:
    t = text.strip()

    # 记： / note:
    if re.match(r"^(记：|记:|note:)", t, flags=re.IGNORECASE):
        content = re.sub(r"^(记：|记:|note:)\s*", "", t, flags=re.IGNORECASE)
        return "store", {"content": content}

    # 找： / search:
    if re.match(r"^(找：|找:|search:)", t, flags=re.IGNORECASE):
        query = re.sub(r"^(找：|找:|search:)\s*", "", t, flags=re.IGNORECASE)
        return "recall", {"query": query}

    # 待办： / todo:
    if re.match(r"^(待办：|待办:|todo:)", t, flags=re.IGNORECASE):
        title = re.sub(r"^(待办：|待办:|todo:)\s*", "", t, flags=re.IGNORECASE)
        return "task", {"op": "add", "title": title}

    if t in {"任务列表", "tasks", "todo list"}:
        return "task", {"op": "list"}

    if t.startswith("完成：") or t.startswith("完成:") or t.lower().startswith("done:"):
        ident = t.split(":", 1)[-1].replace("完成", "").replace("：", "").strip()
        return "task", {"op": "done", "id": ident}

    # 默认：passthrough（先当普通记事）
    return "passthrough", {"content": t}

