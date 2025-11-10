import requests
from utils.logger import get_logger
log = get_logger(__name__)

def http_post(url, **kwargs):
    timeout = kwargs.pop("timeout", 10)
    try:
        resp = requests.post(url, timeout=timeout, **kwargs)
        resp.raise_for_status()
        # 兼容返回 JSON 或纯文本
        try:
            return resp.json()
        except Exception:
            return {"text": resp.text}
    except Exception as e:
        log.error(f"HTTP POST failed: {url} err={e}")
        raise

