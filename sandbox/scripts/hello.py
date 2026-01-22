#!/usr/bin/env python3
"""测试脚本：打印一行并写入 2 个文件。"""
import sys
import json
from pathlib import Path

print("Hello from python_run tool!")

# 写入文件到 sandbox/outputs/
output_dir = Path("outputs")
output_dir.mkdir(parents=True, exist_ok=True)

# 写入第一个文件：a.txt
file_a = output_dir / "a.txt"
file_a.write_text("This is file a.txt\n", encoding="utf-8")
print(f"✓ 已写入文件: {file_a}")

# 写入第二个文件：b.json
file_b = output_dir / "b.json"
file_b.write_text(json.dumps({"message": "This is file b.json", "status": "ok"}, indent=2), encoding="utf-8")
print(f"✓ 已写入文件: {file_b}")

# 如果有参数，也打印出来
if len(sys.argv) > 1:
    print(f"参数: {sys.argv[1:]}")

sys.exit(0)
