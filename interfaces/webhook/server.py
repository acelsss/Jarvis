"""
Webhook 占位：用于接受外部 HTTP 事件，转发给 Controller
后续建议用 FastAPI/Flask 实现：
- POST /jarvis  {text: "..."} -> Controller.handle -> 返回 JSON
"""
def run_webhook():
    print("Webhook server placeholder. TODO: implement with FastAPI/Flask.")

