from core.intent import detect_intent
from core.schemas import Request, Response
from core.formatter import as_text
from core.handlers import note_handler, recall_handler, task_handler
from utils.logger import get_logger
from utils.config import Settings
from memory.openmemory_client import OpenMemoryClient

log = get_logger(__name__)

class Controller:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.mem = OpenMemoryClient(
            base_url=settings.OPENMEMORY_BASE_URL,
            api_key=settings.OPENMEMORY_API_KEY
        )

    def bootstrap(self):
        log.info("Controller bootstrap ok.")

    def handle(self, text: str) -> dict:
        req = Request(text=text, source="cli")
        intent, slots = detect_intent(text)
        req.meta = slots

        if intent == "store":
            resp = note_handler.run(req, self.mem)
        elif intent == "recall":
            resp = recall_handler.run(req, self.mem)
        elif intent == "task":
            resp = task_handler.run(req, self.mem)
        else:
            # 默认当作普通记事写入
            req.meta = {"content": text}
            resp = note_handler.run(req, self.mem)
            if resp.get("ok"):
                resp["intent"] = "passthrough"
                resp["msg"] = "✅ 已保存为普通笔记。"

        # 附加人类可读 msg（兼容 CLI）
        if "msg" not in resp or not resp["msg"]:
            try:
                resp["msg"] = as_text(Response(**resp))
            except Exception:
                pass
        return resp

