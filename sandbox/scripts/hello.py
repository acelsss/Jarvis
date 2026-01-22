#!/usr/bin/env python3
"""测试脚本：打印一行并写入文件。"""
import sys
from pathlib import Path

print("Hello from python_run tool!")

# 写入文件到 sandbox/outputs/
output_dir = Path("outputs")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "hello.txt"
output_file.write_text("Hello from python_run tool!\n", encoding="utf-8")

print(f"✓ 已写入文件: {output_file}")

# 如果有参数，也打印出来
if len(sys.argv) > 1:
    print(f"参数: {sys.argv[1:]}")

sys.exit(0)
