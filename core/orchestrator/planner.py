"""Planning logic."""
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.contracts.task import Task
from core.contracts.skill import Plan, PlanStep
from core.contracts.risk import (
    RISK_LEVEL_R0,
    RISK_LEVEL_R1,
    RISK_LEVEL_R2,
    RISK_LEVEL_R3,
)
from core.llm.schemas import PLAN_SCHEMA
from core.utils.ids import generate_id
from core.prompts.loader import PromptLoader


class Planner:
    """计划器。"""
    
    def __init__(self, sandbox_root: str = "./sandbox"):
        """初始化计划器。
        
        Args:
            sandbox_root: 沙箱根目录
        """
        self.sandbox_root = sandbox_root

    def _truncate_text(self, text: str, max_len: int = 200) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."

    def _summarize_tools(self, tools: Dict[str, Any]) -> List[Dict[str, Any]]:
        summaries = []
        for tool_id, tool in tools.items():
            summaries.append(
                {
                    "id": tool_id,
                    "name": getattr(tool, "name", tool_id),
                    "description": getattr(tool, "description", ""),
                    "risk_level": getattr(tool, "risk_level", RISK_LEVEL_R1),
                }
            )
        return summaries

    def _normalize_risk_level(self, value: Any) -> str:
        if isinstance(value, str):
            normalized = value.strip().upper()
        else:
            normalized = ""
        if normalized in (RISK_LEVEL_R0, RISK_LEVEL_R1, RISK_LEVEL_R2, RISK_LEVEL_R3):
            return normalized
        return RISK_LEVEL_R2

    def _get_llm_model(self, provider: str) -> Optional[str]:
        provider = provider.strip().lower()
        if provider == "openai":
            return os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        if provider == "gemini":
            return os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        return None

    def _log_llm_plan(
        self,
        audit_logger: Any,
        provider: str,
        steps: List[PlanStep],
        notes: str,
    ) -> None:
        if not audit_logger:
            return
        tool_ids = [step.tool_id for step in steps]
        risk_levels = [step.risk_level for step in steps]
        details = {
            "provider": provider,
            "model": self._get_llm_model(provider),
            "steps_count": len(steps),
            "notes": self._truncate_text(notes or ""),
            "tool_ids": tool_ids,
            "risk_levels": risk_levels,
        }
        audit_logger.log("llm.plan", details)

    def _build_file_step(self, task: Task, suffix: str = "") -> PlanStep:
        filename = f"{task.task_id}{suffix}.txt"
        return PlanStep(
            step_id=generate_id("step"),
            tool_id="file",
            description=f"创建任务产物文件: {filename}",
            params={
                "operation": "write",
                "path": f"{self.sandbox_root}/{filename}",
                "content": (
                    f"任务: {task.description}\n"
                    f"创建时间: {datetime.now().isoformat()}\n"
                    f"任务ID: {task.task_id}"
                ),
            },
            risk_level=RISK_LEVEL_R1,
        )

    def _create_rule_plan(
        self,
        task: Task,
        available_tools: Dict[str, Any],
        routed_tools: List[str],
    ) -> Plan:
        plan_id = generate_id("plan")
        steps: List[PlanStep] = []
        available_tools = available_tools or {}
        routed_tools = routed_tools or []
        
        # 确保至少有一个 file_tool 步骤
        has_file_tool = "file" in routed_tools
        
        # 步骤1: 总是创建一个文件作为 artifact
        if "file" in available_tools:
            step1 = PlanStep(
                step_id=generate_id("step"),
                tool_id="file",
                description=f"创建任务产物文件: {task.task_id}.txt",
                params={
                    "operation": "write",
                    "path": f"{self.sandbox_root}/{task.task_id}.txt",
                    "content": (
                        f"任务: {task.description}\n"
                        f"创建时间: {datetime.now().isoformat()}\n"
                        f"任务ID: {task.task_id}"
                    ),
                },
                risk_level=RISK_LEVEL_R1,
            )
            steps.append(step1)
            has_file_tool = True
        
        # 步骤2: 如果路由到其他工具，添加一个步骤
        if routed_tools:
            for tool_id in routed_tools[:2]:  # 最多2个其他工具
                if tool_id == "file" and has_file_tool:
                    continue
                if tool_id in available_tools:
                    # 根据工具类型设置合适的参数
                    if tool_id == "shell":
                        params = {"command": f"echo '处理任务: {task.description}'"}
                        risk_level = RISK_LEVEL_R2
                    else:
                        # 其他工具使用通用参数
                        params = {"operation": "info", "message": f"处理任务: {task.description}"}
                        risk_level = RISK_LEVEL_R1
                    
                    step = PlanStep(
                        step_id=generate_id("step"),
                        tool_id=tool_id,
                        description=f"执行工具: {tool_id}",
                        params=params,
                        risk_level=risk_level,
                    )
                    steps.append(step)
                    if len(steps) >= 3:
                        break
                elif isinstance(tool_id, str) and tool_id.startswith("mcp."):
                    step = PlanStep(
                        step_id=generate_id("step"),
                        tool_id=tool_id,
                        description=f"执行 MCP 工具: {tool_id}",
                        params={},
                        risk_level=RISK_LEVEL_R2,
                    )
                    steps.append(step)
                    if len(steps) >= 3:
                        break
        
        # 如果还没有 file_tool，强制添加一个
        if not has_file_tool and "file" in available_tools:
            step_file = PlanStep(
                step_id=generate_id("step"),
                tool_id="file",
                description=f"创建任务产物文件: {task.task_id}_artifact.txt",
                params={
                    "operation": "write",
                    "path": f"{self.sandbox_root}/{task.task_id}_artifact.txt",
                    "content": (
                        f"任务产物\n任务: {task.description}\n"
                        f"创建时间: {datetime.now().isoformat()}"
                    ),
                },
                risk_level=RISK_LEVEL_R1,
            )
            steps.insert(0, step_file)
        
        # 确保至少有2个步骤
        if len(steps) < 2 and "file" in available_tools:
            step2 = PlanStep(
                step_id=generate_id("step"),
                tool_id="file",
                description=f"创建任务摘要文件: {task.task_id}_summary.txt",
                params={
                    "operation": "write",
                    "path": f"{self.sandbox_root}/{task.task_id}_summary.txt",
                    "content": (
                        f"任务摘要\n任务ID: {task.task_id}\n"
                        f"描述: {task.description}\n状态: {task.status}"
                    ),
                },
                risk_level=RISK_LEVEL_R1,
            )
            steps.append(step2)
        
        return Plan(plan_id=plan_id, steps=steps, estimated_duration=len(steps) * 10)
    
    async def create_plan(
        self,
        task: Task,
        available_tools: Dict[str, Any] = None,
        routed_tools: List[str] = None,
        skill_fulltext: Optional[str] = None,
        llm_client: Any = None,
        audit_logger: Any = None,
        chat_history_messages: Optional[List[Dict[str, str]]] = None,
    ) -> Plan:
        """为任务创建执行计划（生成2-3个步骤，至少包含一个file_tool）。
        
        Args:
            task: 任务对象
            available_tools: 可用工具字典
            routed_tools: 路由后的工具ID列表
            
        Returns:
            执行计划
        """
        available_tools = available_tools or {}
        routed_tools = routed_tools or []

        llm_enabled = os.getenv("LLM_ENABLE_PLANNER") == "1"
        if llm_enabled and llm_client:
            provider = os.getenv("LLM_PROVIDER", "unknown")
            try:
                tools_summary = self._summarize_tools(available_tools)
                
                loader = PromptLoader()
                parsed = loader.parse("planner/default.md")
                
                # 处理 skill_fulltext 条件
                skill_fulltext_section = ""
                if skill_fulltext:
                    skill_fulltext_section = f"\n技能全文如下：\n{skill_fulltext}"
                
                system_prompt = loader.render(
                    parsed["sections"]["system"],
                    {
                        "tools_summary_json": json.dumps(tools_summary, ensure_ascii=False),
                    },
                    strict=True,
                )
                user_prompt = loader.render(
                    parsed["sections"].get("user", ""),
                    {
                        "task_description": task.description,
                        "skill_fulltext_section": skill_fulltext_section,
                    },
                    strict=True,
                )
                try:
                    llm_result = llm_client.complete_json(
                        purpose="plan",
                        system=system_prompt,
                        user=user_prompt,
                        schema_hint=PLAN_SCHEMA,
                        chat_history_messages=chat_history_messages,
                    )
                except Exception as json_err:
                    print(f"LLM 返回的 JSON 解析失败: {json_err}")
                    if os.getenv("DEBUG") == "1":
                        import traceback
                        traceback.print_exc()
                    raise
                
                if isinstance(llm_result, dict):
                    raw_steps = llm_result.get("steps") or []
                    notes = llm_result.get("notes", "")
                    steps: List[PlanStep] = []
                    for raw_step in raw_steps:
                        if not isinstance(raw_step, dict):
                            continue
                        tool_id = raw_step.get("tool_id")
                        if not tool_id:
                            continue
                        is_mcp_tool = isinstance(tool_id, str) and tool_id.startswith("mcp.")
                        if tool_id not in available_tools and not is_mcp_tool:
                            continue
                        description = raw_step.get("description") or f"执行工具: {tool_id}"
                        params = raw_step.get("params")
                        if not isinstance(params, dict):
                            params = {}
                        risk_level = self._normalize_risk_level(raw_step.get("risk_level"))
                        if is_mcp_tool and not raw_step.get("risk_level"):
                            risk_level = RISK_LEVEL_R2
                        steps.append(
                            PlanStep(
                                step_id=generate_id("step"),
                                tool_id=tool_id,
                                description=description,
                                params=params,
                                risk_level=risk_level,
                            )
                        )

                    if steps:
                        if "file" in available_tools and not any(
                            step.tool_id == "file" for step in steps
                        ):
                            steps.insert(0, self._build_file_step(task))

                        plan = Plan(
                            plan_id=generate_id("plan"),
                            steps=steps,
                            estimated_duration=len(steps) * 10,
                        )
                        self._log_llm_plan(audit_logger, provider, steps, notes)
                        return plan
            except Exception as e:
                import traceback
                print(f"LLM 规划不可用，已回退默认规划。错误: {e}")
                if os.getenv("DEBUG") == "1":
                    traceback.print_exc()

        return self._create_rule_plan(task, available_tools, routed_tools)
