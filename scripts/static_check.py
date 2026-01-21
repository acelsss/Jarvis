#!/usr/bin/env python3
"""
静态红线验收脚本：防止路由/QA/风控/审计被破坏。
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    suggestion: str = ""


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _extract_branch_block(text: str, marker: str) -> Tuple[bool, List[str]]:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if marker not in line:
            continue
        indent = len(line) - len(line.lstrip(" "))
        block: List[str] = []
        for sub in lines[idx + 1 :]:
            if not sub.strip():
                block.append(sub)
                continue
            sub_indent = len(sub) - len(sub.lstrip(" "))
            if sub_indent <= indent:
                break
            block.append(sub)
        return True, block
    return False, []


def _check_qa_branch() -> CheckResult:
    path = ROOT / "apps/cli/main.py"
    text = _read_text(path)
    found, block = _extract_branch_block(text, 'route_type == "qa"')
    if not found:
        return CheckResult(
            name="1) QA 分支存在且不调用 planner/toolrunner",
            passed=False,
            detail="未找到 route_type == \"qa\" 分支",
            suggestion="在 CLI 路由中保留 QA 分支并直接返回回答。",
        )

    block_text = "\n".join(block)
    banned = ["planner", "tool_runner", "ToolRunner"]
    if any(token in block_text for token in banned):
        return CheckResult(
            name="1) QA 分支存在且不调用 planner/toolrunner",
            passed=False,
            detail="QA 分支中出现 planner/tool_runner 调用",
            suggestion="确保 QA 分支仅调用 handle_qa 并直接 return。",
        )

    return CheckResult(
        name="1) QA 分支存在且不调用 planner/toolrunner",
        passed=True,
    )


def _check_audit_event_strings() -> CheckResult:
    required = ["llm.route", "llm.qa", "llm.plan", "skill.loaded"]
    found = {key: False for key in required}
    for path in ROOT.rglob("*.py"):
        text = _read_text(path)
        for key in required:
            if key in text:
                found[key] = True
        if all(found.values()):
            break

    missing = [key for key, ok in found.items() if not ok]
    if missing:
        return CheckResult(
            name="2) 审计事件类型字符串存在",
            passed=False,
            detail=f"缺少: {', '.join(missing)}",
            suggestion="检查审计日志事件名是否被改动或删除。",
        )

    return CheckResult(name="2) 审计事件类型字符串存在", passed=True)


def _check_hard_guard_keywords() -> CheckResult:
    path = ROOT / "core/router/route.py"
    text = _read_text(path)
    keywords = ["删除", "rm", "sudo", "支付", "登录", "点击", "输入"]
    if not any(keyword in text for keyword in keywords):
        return CheckResult(
            name="3) Hard Guard 关键词列表存在",
            passed=False,
            detail="未发现关键风险词",
            suggestion="在 hard guard 列表中至少保留 删除/rm/sudo/支付/登录/点击/输入 任意一组。",
        )

    return CheckResult(name="3) Hard Guard 关键词列表存在", passed=True)


def _check_llm_config_docs() -> CheckResult:
    env_text = _read_text(ROOT / ".env.example")
    running_text = _read_text(ROOT / "RUNNING.md")
    merged = env_text + "\n" + running_text
    required = ["LLM_PROVIDER", "LLM_ENABLE_ROUTER", "LLM_ENABLE_PLANNER"]
    missing = [key for key in required if key not in merged]
    if missing:
        return CheckResult(
            name="4) LLM 配置说明存在（.env.example / RUNNING.md）",
            passed=False,
            detail=f"缺少: {', '.join(missing)}",
            suggestion="在 .env.example 或 RUNNING.md 中补充 LLM 相关环境变量说明。",
        )
    return CheckResult(name="4) LLM 配置说明存在（.env.example / RUNNING.md）", passed=True)


def main() -> int:
    checks = [
        _check_qa_branch(),
        _check_audit_event_strings(),
        _check_hard_guard_keywords(),
        _check_llm_config_docs(),
    ]

    failures: List[CheckResult] = []
    for check in checks:
        if check.passed:
            print(f"{check.name}: PASS")
        else:
            print(f"{check.name}: FAIL - {check.detail}")
            if check.suggestion:
                print(f"  建议: {check.suggestion}")
            failures.append(check)

    if failures:
        print("ALL PASS: 否")
        return 1
    print("ALL PASS: 是")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
