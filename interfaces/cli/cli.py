from core.controller import Controller
from utils.config import Settings

def run_cli():
    settings = Settings.load()
    ctrl = Controller(settings)
    ctrl.bootstrap()
    print("Jarvis CLI 已启动。示例：记：今天学习OpenMemory；找：OpenMemory 配置；待办：明天联调。")
    while True:
        try:
            text = input("Jarvis> ").strip()
            if text.lower() in {"exit", "quit"} or text in {"再见", "退出"}:
                print("👋 再见")
                break
            result = ctrl.handle(text)
            msg = result.get("msg") or result
            print(msg)
        except KeyboardInterrupt:
            print("\n👋 再见")
            break

if __name__ == "__main__":
    run_cli()

