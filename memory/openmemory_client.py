"""
OpenMemory 客户端
"""
import requests
from typing import Optional, List, Dict, Any
from utils.logger import get_logger

log = get_logger(__name__)

class OpenMemoryClient:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base = base_url.rstrip("/")
        self.api_key = api_key
    
    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    def store_note(self, content: str):
        """存储笔记"""
        url = f"{self.base}/api/notes"
        payload = {"text": content}
        log.info(f"OpenMemory storing note: {payload}")
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()
    
    def search(self, query: str):
        """搜索记忆"""
        url = f"{self.base}/api/search"
        payload = {"query": query, "top_k": 5}
        log.info(f"OpenMemory searching: {payload}")
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=10)
        resp.raise_for_status()
        return resp.json()

