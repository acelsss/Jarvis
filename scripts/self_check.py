#!/usr/bin/env python3
"""
Jarvis 本地自检脚本：
- LLM-first routing
- QA handler
- progressive skill loading
- 审计/落盘
- 风险门控不旁路
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


AUDIT_PATH = Path("memory/raw_logs/audit.log.jsonl")
TASK_DB_PATH = Path("memory/task_db/tasks.jsonl")
CLI_TIMEOUT_SECONDS = 180


@dataclass
class CaseResult:
    name: str
    status: str  # PASS / FAIL / SKIP
    reason: str = ""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def _read_jsonl_from_line(path: Path, start_line: int) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    entries: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for idx, line in enumerate(f, start=1):
            if idx <= start_line:
                continue
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _llm_configured() -> Tuple[bool, str]:
    provider = (os.getenv("LLM_PROVIDER") or "").strip().lower()
    if not provider or provider == "none":
        return False, "LLM_PROVIDER 未配置"
    if provider == "openai":
        if not (os.getenv("OPENAI_API_KEY") or "").strip():
            return False, "OPENAI_API_KEY 未配置"
        return True, "ok"
    if provider == "gemini":
        if not (os.getenv("GEMINI_API_KEY") or "").strip():
            return False, "GEMINI_API_KEY 未配置"
        return True, "ok"
    return False, f"未知 LLM_PROVIDER: {provider}"


def _run_cli(input_text: str) -> Tuple[int, str]:
    env = os.environ.copy()
    env["LLM_ENABLE_ROUTER"] = "1"
    env["LLM_ENABLE_PLANNER"] = "1"
    cmd = [sys.executable, "-m", "apps.cli.main"]
    try:
        completed = subprocess.run(
            cmd,
            input=input_text,
            text=True,
            capture_output=True,
            cwd=_repo_root(),
            env=env,
            timeout=CLI_TIMEOUT_SECONDS,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        return completed.returncode, output
    except subprocess.TimeoutExpired as exc:
        return 124, (exc.stdout or "") + (exc.stderr or "")


def _has_event(entries: List[Dict[str, Any]], event_type: str) -> bool:
    return any(entry.get("event_type") == event_type for entry in entries)


def _has_route_type(entries: List[Dict[str, Any]], route_type: str) -> bool:
    for entry in entries:
        if entry.get("event_type") != "llm.route":
            continue
        details = entry.get("details") or {}
        if details.get("route_type") == route_type:
            return True
    return False


def _case1_qa(llm_ready: bool, llm_reason: str) -> Tuple[CaseResult, List[Dict[str, Any]]]:
    name = "CASE1 QA"
    if not llm_ready:
        return CaseResult(name=name, status="SKIP", reason=f"LLM 未配置: {llm_reason}"), []

    start_line = _count_lines(AUDIT_PATH)
    rc, output = _run_cli("你好，介绍一下你自己。\nno\n")
    entries = _read_jsonl_from_line(AUDIT_PATH, start_line)

    if rc != 0:
        return CaseResult(name=name, status="FAIL", reason="CLI 返回非 0"), entries

    forbidden = ["生成执行计划", "执行工具", "需要审批"]
    if any(token in output for token in forbidden):
        return CaseResult(name=name, status="FAIL", reason="输出出现规划/执行/审批"), entries

    if not (_has_event(entries, "llm.qa") or _has_route_type(entries, "qa")):
        return CaseResult(name=name, status="FAIL", reason="审计未命中 llm.qa 或 qa 路由"), entries

    return CaseResult(name=name, status="PASS"), entries


def _case2_clarify(llm_ready: bool, llm_reason: str) -> Tuple[CaseResult, List[Dict[str, Any]]]:
    name = "CASE2 clarify"
    if not llm_ready:
        return CaseResult(name=name, status="SKIP", reason=f"LLM 未配置: {llm_reason}"), []

    start_line = _count_lines(AUDIT_PATH)
    rc, output = _run_cli("帮我搞一下这个\nno\n")
    entries = _read_jsonl_from_line(AUDIT_PATH, start_line)

    if rc != 0:
        return CaseResult(name=name, status="FAIL", reason="CLI 返回非 0"), entries

    if "生成执行计划" in output or "[7/8] 执行工具" in output or "执行工具" in output:
        return CaseResult(name=name, status="FAIL", reason="触发了规划/执行"), entries

    has_clarify_output = ("澄清问题" in output) or ("需要澄清" in output)
    has_clarify_audit = _has_route_type(entries, "clarify")
    if not (has_clarify_output or has_clarify_audit):
        return CaseResult(name=name, status="FAIL", reason="未触发澄清"), entries

    return CaseResult(name=name, status="PASS"), entries


def _case3_hard_guard() -> Tuple[CaseResult, List[Dict[str, Any]]]:
    name = "CASE3 hard-guard"
    start_line = _count_lines(AUDIT_PATH)
    rc, output = _run_cli("帮我删除 sandbox 下所有文件\nno\n")
    entries = _read_jsonl_from_line(AUDIT_PATH, start_line)

    if rc != 0:
        return CaseResult(name=name, status="FAIL", reason="CLI 返回非 0"), entries

    if "[6/8] 风险评估" not in output:
        return CaseResult(name=name, status="FAIL", reason="未进入风险评估"), entries

    if ("需要审批" not in output) and ("是否批准执行" not in output):
        return CaseResult(name=name, status="FAIL", reason="未触发审批"), entries

    if "已拒绝" not in output:
        return CaseResult(name=name, status="FAIL", reason="未拒绝高风险执行"), entries

    if "[7/8] 执行工具" in output or "执行成功" in output:
        return CaseResult(name=name, status="FAIL", reason="出现执行动作"), entries

    return CaseResult(name=name, status="PASS"), entries


def _case4_skill() -> Tuple[CaseResult, List[Dict[str, Any]]]:
    name = "CASE4 skill"
    start_line = _count_lines(AUDIT_PATH)
    rc, output = _run_cli("写一篇 wechat 公众号文章大纲，主题是 AI 与教育融合\nno\n")
    entries = _read_jsonl_from_line(AUDIT_PATH, start_line)

    if rc != 0:
        return CaseResult(name=name, status="FAIL", reason="CLI 返回非 0"), entries

    if "匹配到技能" not in output:
        return CaseResult(name=name, status="FAIL", reason="未匹配技能"), entries

    if "生成执行计划" not in output:
        return CaseResult(name=name, status="FAIL", reason="未生成计划"), entries

    if "[6/8] 风险评估" not in output:
        return CaseResult(name=name, status="FAIL", reason="未进入风险评估"), entries

    if not _has_event(entries, "skill.loaded"):
        return CaseResult(name=name, status="FAIL", reason="未记录 skill.loaded"), entries

    return CaseResult(name=name, status="PASS"), entries


def main() -> int:
    repo_root = _repo_root()
    os.chdir(repo_root)

    audit_before = _count_lines(AUDIT_PATH)
    tasks_before = _count_lines(TASK_DB_PATH)

    llm_ready, llm_reason = _llm_configured()

    results: List[CaseResult] = []
    all_new_audit: List[Dict[str, Any]] = []

    case1, entries1 = _case1_qa(llm_ready, llm_reason)
    results.append(case1)
    all_new_audit.extend(entries1)

    case2, entries2 = _case2_clarify(llm_ready, llm_reason)
    results.append(case2)
    all_new_audit.extend(entries2)

    case3, entries3 = _case3_hard_guard()
    results.append(case3)
    all_new_audit.extend(entries3)

    case4, entries4 = _case4_skill()
    results.append(case4)
    all_new_audit.extend(entries4)

    audit_after = _count_lines(AUDIT_PATH)
    tasks_after = _count_lines(TASK_DB_PATH)

    failures: List[str] = []
    for result in results:
        if result.status == "PASS":
            print(f"{result.name}: PASS")
        elif result.status == "SKIP":
            print(f"{result.name}: SKIP - {result.reason}")
        else:
            print(f"{result.name}: FAIL - {result.reason}")
            failures.append(f"{result.name}: {result.reason}")

    if audit_after <= audit_before:
        failures.append("审计日志未新增")
    else:
        if not _has_event(all_new_audit, "skill.loaded"):
            failures.append("审计缺少 skill.loaded")
        if llm_ready and not (
            _has_event(all_new_audit, "llm.qa")
            or _has_event(all_new_audit, "llm.plan")
            or _has_event(all_new_audit, "llm.route")
        ):
            failures.append("审计缺少 llm.route/llm.qa/llm.plan")

    if tasks_after <= tasks_before:
        failures.append("任务库未新增记录")

    if failures:
        print("ALL PASS: 否")
        print("失败原因:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("ALL PASS: 是")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
