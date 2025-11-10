import requests
from typing import Optional, Dict, Any
from utils.logger import get_logger
log = get_logger(__name__)

def request_json(method: str, url: str, headers: Optional[Dict[str, str]] = None, 
                 json: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Dict[str, Any]:
    """
    统一的 JSON 请求函数
    
    Args:
        method: HTTP 方法（GET, POST, PUT, DELETE）
        url: 请求 URL
        headers: 请求头
        json: JSON 请求体
        timeout: 超时时间（秒）
    
    Returns:
        响应 JSON 字典
    
    Raises:
        requests.RequestException: 请求失败时抛出
    """
    try:
        resp = requests.request(method, url, headers=headers, json=json, timeout=timeout)
        resp.raise_for_status()
        # 兼容返回 JSON 或纯文本
        try:
            return resp.json()
        except Exception:
            return {"text": resp.text}
    except Exception as e:
        log.error(f"HTTP {method} failed: {url} err={e}")
        raise

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

