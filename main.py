from utils.logger import get_logger
from utils.config import Settings
from core.controller import Controller

log = get_logger(__name__)

def main():
    settings = Settings.load()
    log.info("Jarvis starting…")
    controller = Controller(settings)
    controller.bootstrap()

    # 示例最小交互（可在 CLI 模块里使用）
    demo = "记：今天把 OpenMemory 的 /api/notes 和 /api/search 接上。"
    result = controller.handle(demo)
    log.info(f"Demo result: {result.get('msg', result)}")

if __name__ == "__main__":
    main()
