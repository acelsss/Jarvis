"""
Memory Search CLI：从终端检索 OpenMemory 记录
"""
from __future__ import annotations
import sys
import argparse
from typing import List, Optional
from utils.config import Settings
from utils.logger import get_logger
from core.memory.client import MemoryClient
from core.memory.types import SearchResult

log = get_logger(__name__)

def format_content(content: str, max_len: int = 100) -> str:
    """安全截断内容"""
    if len(content) <= max_len:
        return content
    return content[:max_len - 3] + "..."

def format_timestamp(ts: Optional[str]) -> str:
    """格式化时间戳"""
    if not ts:
        return ""
    try:
        # 尝试解析 ISO 格式
        from datetime import datetime
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return ts[:16] if len(ts) > 16 else ts

def print_table(results: List[SearchResult]):
    """打印结果表格"""
    if not results:
        print("No results.")
        return
    
    # 计算列宽
    max_idx_len = len(str(len(results)))
    max_type_len = max(len(r.type or "") for r in results) if any(r.type for r in results) else 0
    max_type_len = max(max_type_len, 4)  # 至少 "type" 的长度
    max_content_len = 80  # 固定内容列宽
    max_ts_len = 16  # 时间戳列宽
    max_score_len = 6  # 分数列宽
    
    # 表头
    header = f"{'#':<{max_idx_len}} | {'type':<{max_type_len}} | {'content':<{max_content_len}} | {'timestamp':<{max_ts_len}} | {'score':<{max_score_len}}"
    print(header)
    print("-" * len(header))
    
    # 数据行
    for i, result in enumerate(results, 1):
        idx = str(i)
        type_str = result.type or ""
        content = format_content(result.content or "", max_content_len)
        ts = format_timestamp(result.timestamp)
        score = f"{result.score:.3f}" if result.score is not None else ""
        
        row = f"{idx:<{max_idx_len}} | {type_str:<{max_type_len}} | {content:<{max_content_len}} | {ts:<{max_ts_len}} | {score:<{max_score_len}}"
        print(row)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Search OpenMemory records from terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-q", "--q",
        required=True,
        help="Search query (required)"
    )
    parser.add_argument(
        "-n", "--limit",
        type=int,
        help="Maximum number of results (default: from config)"
    )
    parser.add_argument(
        "-x", "--exclude",
        help="Comma-separated list of types to exclude (default: from config)"
    )
    
    args = parser.parse_args()
    
    try:
        # 加载配置
        settings = Settings.load()
        om_config = settings.om
        
        # 解析参数
        query = args.q
        limit = args.limit if args.limit is not None else om_config.search_limit
        exclude_types = None
        
        if args.exclude:
            exclude_types = [t.strip() for t in args.exclude.split(",") if t.strip()]
        else:
            exclude_types = om_config.exclude_types
        
        # 创建客户端
        client = MemoryClient(om_config, logger=log)
        
        # 执行检索
        log.info(f"Searching: query='{query}', limit={limit}, exclude={exclude_types}")
        results = client.search(
            query_text=query,
            limit=limit,
            exclude_types=exclude_types
        )
        
        # 打印结果
        print_table(results)
        
        return 0
    
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 1
    except Exception as e:
        log.error(f"Error: {type(e).__name__}: {e}")
        print(f"Error: {type(e).__name__}: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

