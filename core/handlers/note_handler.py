from core.schemas import Request, Response
from utils.logger import get_logger
from memory.openmemory_client import OpenMemoryClient

log = get_logger(__name__)

def run(req: Request, mem: OpenMemoryClient) -> dict:
    content = req.meta.get("content") if req.meta else req.text
    try:
        # 假设接口为 /api/notes；如与你部署的不同，请在 memory 客户端改
        mem.store_note(content)
        return Response(ok=True, intent="store", msg="ok").__dict__
    except Exception as e:
        log.exception("store_note failed")
        return Response(ok=False, intent="store", msg=f"写入失败：{e}").__dict__

