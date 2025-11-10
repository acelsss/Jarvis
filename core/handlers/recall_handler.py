from core.schemas import Request, Response
from utils.logger import get_logger
from memory.client_openmemory import OpenMemoryClient

log = get_logger(__name__)

def run(req: Request, mem: OpenMemoryClient) -> dict:
    query = (req.meta or {}).get("query") or req.text
    try:
        # 假设接口为 /api/search；根据你的 OpenMemory 调整
        data = mem.search(query)
        return Response(ok=True, intent="recall", msg="ok", data={"items": data}).__dict__
    except Exception as e:
        log.exception("search failed")
        return Response(ok=False, intent="recall", msg=f"检索失败：{e}").__dict__

