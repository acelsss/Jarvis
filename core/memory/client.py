"""
MemoryClient：OpenMemory 客户端（端点自适配、重试、本地队列）
"""
from __future__ import annotations
import json
import time
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from utils.http import request_json
from utils.logger import get_logger
from utils.config import OpenMemoryConfig
from core.memory.types import MemoryItem, SearchResult, make_memory_item

log = get_logger(__name__)

PENDING_FILE = Path("data/pending-memories.jsonl")

class MemoryClient:
    """OpenMemory 客户端（支持端点自适配、重试、本地队列）"""
    
    def __init__(self, cfg: OpenMemoryConfig, logger=None):
        """
        初始化客户端
        
        Args:
            cfg: OpenMemory 配置
            logger: 可选的自定义日志器
        """
        self.cfg = cfg
        self.log = logger or log
        self.timeout = cfg.timeout_ms / 1000.0  # 转换为秒
        
        # 构建默认 headers
        self.headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            self.headers["Authorization"] = f"Bearer {cfg.api_key}"
        
        # 端点候选列表
        if cfg.endpoint_store:
            self.store_candidates = [cfg.endpoint_store]
        else:
            self.store_candidates = ["/memories", "/api/memories", "/v1/memories"]
        
        if cfg.endpoint_search:
            self.search_candidates = [cfg.endpoint_search]
        else:
            self.search_candidates = ["/search", "/api/search", "/memories/search", "/v1/search"]
        
        # 确保 pending 目录存在
        PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    def _full_url(self, path: str) -> str:
        """拼接完整 URL（处理多余斜杠）"""
        base = self.cfg.base_url.rstrip("/")
        path = path.lstrip("/")
        return f"{base}/{path}"
    
    def _try_endpoints(
        self, 
        candidates: List[str], 
        payload: Dict[str, Any], 
        op_name: str
    ) -> Tuple[Dict[str, Any], str]:
        """
        尝试多个端点，使用指数退避重试
        
        Args:
            candidates: 端点候选列表
            payload: 请求体
            op_name: 操作名称（用于日志）
        
        Returns:
            (响应 JSON, 使用的端点路径)
        
        Raises:
            Exception: 所有端点都失败时抛出
        """
        last_error = None
        
        for candidate in candidates:
            url = self._full_url(candidate)
            retry_delays = [0.5, 1.0, 2.0]
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    # 日志摘要（限制200字符）
                    payload_summary = json.dumps(payload, ensure_ascii=False)[:200]
                    if len(json.dumps(payload, ensure_ascii=False)) > 200:
                        payload_summary += "..."
                    
                    self.log.info(f"[{op_name}] Trying {candidate} (attempt {attempt + 1}/{max_retries})")
                    self.log.debug(f"Payload: {payload_summary}")
                    
                    resp = request_json(
                        method="POST",
                        url=url,
                        headers=self.headers,
                        json=payload,
                        timeout=self.timeout
                    )
                    
                    self.log.info(f"[{op_name}] Success: {candidate} (status 2xx)")
                    return resp, candidate
                
                except Exception as e:
                    last_error = e
                    status_code = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
                    
                    # 4xx 错误直接失败，不重试
                    if status_code and 400 <= status_code < 500:
                        self.log.warning(f"[{op_name}] Client error {status_code} on {candidate}: {type(e).__name__}")
                        break
                    
                    # 5xx 或网络错误：指数退避重试
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        self.log.warning(
                            f"[{op_name}] Failed on {candidate} (attempt {attempt + 1}): {type(e).__name__}, "
                            f"retrying in {delay}s"
                        )
                        time.sleep(delay)
                    else:
                        self.log.error(f"[{op_name}] Failed on {candidate} after {max_retries} attempts: {type(e).__name__}")
        
        # 所有端点都失败
        raise Exception(f"[{op_name}] All endpoints failed. Last error: {last_error}")
    
    def store(self, item: MemoryItem) -> Dict[str, Any]:
        """
        存储记忆项
        
        Args:
            item: 记忆项
        
        Returns:
            成功：{"id": <可选>, "path": <使用端点>}
            失败：{"queued": True, "reason": "..."}
        """
        # 确保有 timestamp
        if not item.timestamp:
            from datetime import datetime, timezone
            item.timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        
        payload = item.to_dict()
        
        try:
            resp, path_used = self._try_endpoints(self.store_candidates, payload, "store")
            
            result = {"path": path_used}
            if "id" in resp:
                result["id"] = resp["id"]
            elif "_id" in resp:
                result["id"] = resp["_id"]
            
            return result
        
        except Exception as e:
            # 失败：写入本地待补队列
            self.log.warning(f"store failed, queuing to local: {type(e).__name__}: {e}")
            
            # 追加到 JSONL 文件
            item_dict = item.to_dict()
            with open(PENDING_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(item_dict, ensure_ascii=False) + "\n")
            
            return {
                "queued": True,
                "reason": f"{type(e).__name__}: {str(e)[:100]}"
            }
    
    def search(
        self, 
        query_text: str, 
        limit: Optional[int] = None, 
        exclude_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        搜索记忆
        
        Args:
            query_text: 查询文本
            limit: 结果数量限制（默认使用配置值）
            exclude_types: 排除的类型（默认使用配置值）
        
        Returns:
            搜索结果列表
        """
        limit = limit or self.cfg.search_limit
        exclude_types = exclude_types or self.cfg.exclude_types
        
        payload = {
            "text": query_text,
            "limit": limit
        }
        
        if exclude_types:
            payload["exclude_types"] = exclude_types
        
        try:
            resp, _ = self._try_endpoints(self.search_candidates, payload, "search")
            
            # 统一映射响应为 SearchResult 列表
            results = []
            
            # 处理不同的响应格式
            items = resp
            if isinstance(resp, dict):
                items = resp.get("items", resp.get("results", resp.get("data", [])))
            
            for item in items:
                if isinstance(item, dict):
                    result = SearchResult(
                        id=item.get("id") or item.get("id_") or item.get("_id"),
                        type=item.get("type"),
                        content=item.get("content") or item.get("text") or item.get("body", ""),
                        timestamp=item.get("timestamp") or item.get("ts") or item.get("time"),
                        score=item.get("score") or item.get("relevance"),
                        source=item.get("source"),
                        extras=item.get("extras") or item.get("meta")
                    )
                    results.append(result)
            
            return results
        
        except Exception as e:
            self.log.error(f"search failed: {type(e).__name__}: {e}")
            return []
    
    def flush_pending(self) -> Dict[str, Any]:
        """
        刷新待补队列：重试所有待处理的记忆项
        
        Returns:
            {"processed": <数量>, "succeeded": <数量>, "failed": <数量>}
        """
        if not PENDING_FILE.exists():
            return {"processed": 0, "succeeded": 0, "failed": 0}
        
        # 读取所有待处理项
        pending_items = []
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        pending_items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        
        if not pending_items:
            return {"processed": 0, "succeeded": 0, "failed": 0}
        
        self.log.info(f"Flushing {len(pending_items)} pending items...")
        
        succeeded = []
        failed = []
        
        for item_dict in pending_items:
            try:
                # 重建 MemoryItem
                item = MemoryItem(**item_dict)
                result = self.store(item)
                
                if result.get("queued"):
                    # 仍然失败，保留
                    failed.append(item_dict)
                else:
                    # 成功
                    succeeded.append(item_dict)
                    self.log.debug(f"Successfully flushed item: {item.content[:50]}")
            
            except Exception as e:
                self.log.error(f"Error flushing item: {type(e).__name__}: {e}")
                failed.append(item_dict)
        
        # 原子写：先写临时文件再替换
        if failed:
            temp_file = PENDING_FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                for item in failed:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            temp_file.replace(PENDING_FILE)
        else:
            # 全部成功，删除文件
            PENDING_FILE.unlink()
        
        return {
            "processed": len(pending_items),
            "succeeded": len(succeeded),
            "failed": len(failed)
        }


if __name__ == "__main__":
    # 轻度自测脚本
    from utils.config import Settings
    
    settings = Settings.load()
    client = MemoryClient(settings.om)
    
    # 测试 store
    print("=== Testing store ===")
    test_item = make_memory_item(
        content="测试：我喜欢手冲咖啡，不加糖",
        default_type=settings.om.store_default_type
    )
    store_result = client.store(test_item)
    print(f"Store result: {store_result}")
    
    # 测试 search
    print("\n=== Testing search ===")
    search_results = client.search("咖啡", limit=2)
    print(f"Found {len(search_results)} results")
    for i, result in enumerate(search_results[:2], 1):
        print(f"{i}. [{result.score or 'N/A'}] {result.content[:50]}...")

