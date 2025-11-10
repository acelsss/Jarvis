from datetime import datetime, timedelta, timezone

def now_iso():
    return datetime.now().isoformat(timespec="seconds")

def to_iso(ts: float):
    return datetime.fromtimestamp(ts).isoformat(timespec="seconds")

