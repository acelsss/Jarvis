#!/usr/bin/env bash
set -e
python - << 'PY'
from utils.config import Settings
import requests
s = Settings.load()
try:
    r = requests.get(s.OPENMEMORY_BASE_URL + "/healthz", timeout=3)
    print("OpenMemory:", r.status_code)
except Exception as e:
    print("OpenMemory not reachable:", e)
print("✅ Jarvis health script done.")
PY

