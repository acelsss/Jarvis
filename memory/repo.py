from utils.logger import get_logger
from memory.client_openmemory import OpenMemoryClient
from memory.local_cache import json_store

log = get_logger(__name__)

class MemoryRepo:
    """
    统一记忆仓库：
    - 优先写/读 OpenMemory
    - 失败回退本地 json_store
    """
    def __init__(self, client: OpenMemoryClient):
        self.client = client

    def store(self, text: str, source: str = "jarvis"):
        try:
            self.client.store_note(text, source)
            return {"ok": True, "remote": True}
        except Exception as e:
            log.warning(f"remote store failed, fallback local: {e}")
            json_store.add_note(text, source)
            return {"ok": True, "remote": False, "fallback": "local"}

    def search(self, query: str, top_k: int = 5):
        try:
            return self.client.search(query, top_k)
        except Exception as e:
            log.warning(f"remote search failed, fallback local: {e}")
            return json_store.search(query, top_k)

