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
from core.memory.types import MemoryItem, SearchResult, StoreResult, make_memory_item

log = get_logger(__name__)

PENDING_FILE = Path("data/pending-memories.jsonl")


def _format_timestamp(ts: Any) -> Optional[str]:
    """
    格式化时间戳为本地时间字符串（YYYY-MM-DD HH:MM）
    
    Args:
        ts: 时间戳（可能是毫秒整数、ISO 字符串等）
        
    Returns:
        格式化的时间字符串，或 None
    """
    if ts is None:
        return None
    
    try:
        from datetime import datetime
        
        # 如果是数字（毫秒时间戳）
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000.0 if ts > 1e10 else ts)
            return dt.strftime("%Y-%m-%d %H:%M")
        
        # 如果是字符串
        if isinstance(ts, str):
            # 尝试解析为数字
            try:
                ts_num = float(ts)
                if ts_num > 1e10:  # 毫秒时间戳
                    dt = datetime.fromtimestamp(ts_num / 1000.0)
                else:  # 秒时间戳
                    dt = datetime.fromtimestamp(ts_num)
                return dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                # 尝试解析 ISO 格式
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d %H:%M")
        
        return None
    except Exception:
        return None

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
    
    def store(self, item: MemoryItem) -> StoreResult:
        """
        存储记忆项
        
        Args:
            item: 记忆项
        
        Returns:
            StoreResult: 存储结果（包含 status: "new"/"dedup"）
        """
        # 确保有 timestamp
        if not item.timestamp:
            from datetime import datetime, timezone
            item.timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        
        # 先尝试第一个候选端点，判断是否为 v2 接口
        first_candidate = self.store_candidates[0] if self.store_candidates else ""
        is_v2_store = first_candidate.endswith("/memory/add") or first_candidate == "/memory/add"
        
        if is_v2_store:
            # v2 格式：{"content": "<文本>", "user_id": "<用户ID>", "tags": [...], "metadata": {...}}
            payload = {
                "content": item.content,
                "user_id": self.cfg.user_id or "default"
            }
            # 如果 item 包含 tags 和 metadata（从 source/extras 提取）
            if item.source and isinstance(item.source, dict):
                # 尝试从 source 中提取 tags
                if "tags" in item.source:
                    payload["tags"] = item.source["tags"]
            if item.extras:
                # extras 作为 metadata
                payload["metadata"] = item.extras
        else:
            # 兼容原有格式
            payload = item.to_dict()
        
        try:
            resp, path_used = self._try_endpoints(self.store_candidates, payload, "store")
            self.log.info(f"[store] Used endpoint: {path_used}")
            
            # 解析 deduplicated 字段
            deduplicated = resp.get("deduplicated", False)
            status = "dedup" if deduplicated else "new"
            
            # 提取 node_id
            node_id = resp.get("id") or resp.get("_id") or resp.get("node_id")
            
            return StoreResult(
                status=status,
                node_id=node_id,
                raw=resp
            )
        
        except Exception as e:
            # 失败：写入本地待补队列
            self.log.warning(f"[Jarvis][store] Failed, queuing to local: {type(e).__name__}: {e}")
            
            # 追加到 JSONL 文件
            item_dict = item.to_dict()
            with open(PENDING_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(item_dict, ensure_ascii=False) + "\n")
            
            # 返回一个表示失败的结果（status 设为 "error"）
            return StoreResult(
                status="error",
                node_id=None,
                raw={"queued": True, "reason": f"{type(e).__name__}: {str(e)[:100]}"}
            )
    
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
        
        # 判断是否为 v2 接口
        first_candidate = self.search_candidates[0] if self.search_candidates else ""
        is_v2_query = first_candidate.endswith("/memory/query") or first_candidate == "/memory/query"
        
        if is_v2_query:
            # v2 格式：{"query": "<关键词>", "k": <int>, "filters": {"user_id": "<用户ID>"}}
            payload = {
                "query": query_text,
                "k": limit
            }
            if self.cfg.user_id:
                payload["filters"] = {"user_id": self.cfg.user_id}
        else:
            # 兼容原有格式
            payload = {
                "text": query_text,
                "limit": limit
            }
            if exclude_types:
                payload["exclude_types"] = exclude_types
        
        try:
            resp, path_used = self._try_endpoints(self.search_candidates, payload, "search")
            self.log.info(f"[search] Used endpoint: {path_used}")
            
            # 统一映射响应为 SearchResult 列表
            results = []
            
            if is_v2_query:
                # v2 响应格式：{"query": "...", "matches": [...]}
                data = resp
                matches = data.get("matches", [])
                
                for m in matches:
                    if isinstance(m, dict):
                        # 提取时间戳（优先 last_seen_at，否则 created_at）
                        timestamp_str = None
                        raw_timestamp = None
                        
                        # 尝试提取 last_seen_at（可能是毫秒时间戳或 ISO 字符串）
                        if "last_seen_at" in m:
                            raw_timestamp = m["last_seen_at"]
                            timestamp_str = _format_timestamp(raw_timestamp)
                        elif "created_at" in m:
                            raw_timestamp = m["created_at"]
                            timestamp_str = _format_timestamp(raw_timestamp)
                        
                        # 提取 extras 字段
                        extras = {}
                        for k in ("sectors", "path", "salience", "last_seen_at", "created_at"):
                            if k in m:
                                extras[k] = m[k]
                        
                        result = SearchResult(
                            id=m.get("id"),
                            type=m.get("primary_sector"),
                            content=m.get("content", ""),
                            timestamp=timestamp_str,  # 格式化的时间字符串
                            score=m.get("score"),
                            source=None,
                            extras=extras if extras else None,
                            raw=m.copy()  # 保存原始数据
                        )
                        results.append(result)
            else:
                # 兼容原有响应格式
                items = resp
                if isinstance(resp, dict):
                    items = resp.get("items", resp.get("results", resp.get("data", [])))
                
                for item in items:
                    if isinstance(item, dict):
                        # 提取时间戳
                        raw_timestamp = item.get("timestamp") or item.get("ts") or item.get("time")
                        timestamp_str = _format_timestamp(raw_timestamp) if raw_timestamp else None
                        
                        result = SearchResult(
                            id=item.get("id") or item.get("id_") or item.get("_id"),
                            type=item.get("type"),
                            content=item.get("content") or item.get("text") or item.get("body", ""),
                            timestamp=timestamp_str,
                            score=item.get("score") or item.get("relevance"),
                            source=item.get("source"),
                            extras=item.get("extras") or item.get("meta"),
                            raw=item.copy()  # 保存原始数据
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
    print(f"OM_USER_ID: {settings.om.user_id}")
    print(f"OM_ENDPOINT_STORE: {settings.om.endpoint_store}")
    print(f"OM_ENDPOINT_SEARCH: {settings.om.endpoint_search}")
    
    client = MemoryClient(settings.om)
    
    # 测试 store
    print("\n=== Testing store ===")
    test_item = make_memory_item(
        content="测试：我喜欢手冲咖啡，不加糖",
        default_type=settings.om.store_default_type
    )
    store_result = client.store(test_item)
    print(f"Store result: {store_result}")
    
    # 测试 search
    print("\n=== Testing search ===")
    search_results = client.search("咖啡", limit=1)
    print(f"Found {len(search_results)} results")
    if search_results:
        result = search_results[0]
        print(f"First result: [{result.score or 'N/A'}] {result.content[:50]}...")
        print(f"  Type: {result.type}, ID: {result.id}")
    else:
        print("No results found.")

