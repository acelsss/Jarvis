"""Audit logging."""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class AuditLogger:
    """审计日志记录器（JSONL格式）。"""
    
    def __init__(self, log_path: str = "./memory/raw_logs/audit.log.jsonl"):
        """初始化审计日志记录器。
        
        Args:
            log_path: 日志文件路径（JSONL格式）
        """
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
    
    def log(self, event_type: str, details: Dict[str, Any]) -> None:
        """记录审计事件（JSONL格式）。
        
        Args:
            event_type: 事件类型
            details: 事件详情
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "details": details,
        }
        
        # 追加模式写入 JSONL（每行一个 JSON 对象）
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
