import requests
from utils.logger import get_logger
from utils.http import http_post

log = get_logger(__name__)

class OpenMemoryClient:
    def __init__(self, base_url: str, api_key: str = ""):
        self.base = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def store_note(self, text: str, source: str = "jarvis"):
        url = f"{self.base}/api/notes"
        payload = {"text": text, "source": source}
        return http_post(url, json=payload, headers=self._headers(), timeout=10)

    def search(self, query: str, top_k: int = 5):
        url = f"{self.base}/api/search"
        payload = {"query": query, "top_k": top_k}
        return http_post(url, json=payload, headers=self._headers(), timeout=10)

