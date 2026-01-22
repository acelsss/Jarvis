#!/usr/bin/env python3
"""演示脚本：生成一个简单的输出文件。"""
from pathlib import Path

print("Demo script executed!")

# 写入文件到 sandbox/outputs/
output_dir = Path("outputs")
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / "demo_output.txt"
output_file.write_text("This is output from demo.py\n", encoding="utf-8")

print(f"✓ 已写入文件: {output_file}")
