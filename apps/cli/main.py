"""CLI main entry point."""
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    # 加载 .env 文件
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv 未安装时忽略

from core.contracts.task import (
    TASK_STATUS_NEW,
    TASK_STATUS_CONTEXT_BUILT,
    TASK_STATUS_PLANNED,
    TASK_STATUS_WAITING_APPROVAL,
    TASK_STATUS_APPROVED,
    TASK_STATUS_RUNNING,
    TASK_STATUS_COMPLETED,
)
from core.orchestrator.task_manager import TaskManager
from core.orchestrator.planner import Planner
from core.orchestrator.approval_gate import ApprovalGate
from core.orchestrator.executor import Executor
from core.orchestrator.qa_handler import handle_qa
from core.context_engine.build_context import build_context, search_openmemory
from core.router.route import route_task, route_llm_first
from core.llm.factory import build_llm_client
from core.platform.audit import AuditLogger
from core.platform.config import Config
from core.capabilities.index_builder import build_capability_index
from tools.registry import ToolRegistry
from tools.runner import ToolRunner
from tools.local.shell_tool import ShellTool
from tools.local.file_tool import FileTool
from tools.python_run import PythonRunTool
from skills.registry import SkillsRegistry
from skills.runtime.to_plan import skill_to_plan


async def main():
    """主函数 - Kernel MVP 最小闭环。"""
    print("=" * 60)
    print("Jarvis v0.1 - Kernel MVP")
    print("=" * 60)
    
    # 初始化组件
    config = Config()
    preferences = config.load_yaml("preferences.yaml")
    sandbox_root = preferences.get("sandbox", {}).get("sandbox_root", "./sandbox")
    
    task_manager = TaskManager()
    planner = Planner(sandbox_root=sandbox_root)
    approval_gate = ApprovalGate()
    executor = Executor()
    audit_logger = AuditLogger()
    tool_registry = ToolRegistry()
    tool_runner = ToolRunner()
    
    # 初始化技能注册表
    skills_registry = SkillsRegistry(workspace_dir="./skills_workspace")
    skills_registry.scan_workspace()
    
    # 注册工具
    file_tool = FileTool(sandbox_root=sandbox_root)
    shell_tool = ShellTool()
    python_run_tool = PythonRunTool()
    tool_registry.register(file_tool)
    tool_registry.register(shell_tool)
    tool_registry.register(python_run_tool)
    
    # 1. CLI 输入
    if len(sys.argv) > 1:
        description = " ".join(sys.argv[1:])
    else:
        description = input("\n请输入任务描述 (输入 /skills 查看可用技能): ").strip()
    
    # 处理特殊命令
    if description == "/skills":
        print("\n" + "=" * 60)
        print("已加载的技能列表")
        print("=" * 60)
        skills = skills_registry.list_all()
        if not skills:
            print("暂无已加载的技能")
        else:
            for skill_id, skill in skills.items():
                print(f"\n技能ID: {skill_id}")
                print(f"  名称: {skill.name}")
                print(f"  描述: {skill.description}")
                print(f"  标签: {', '.join(skill.tags) if skill.tags else '无'}")
                if skill.file_path:
                    print(f"  路径: {skill.file_path}")
        print("\n" + "=" * 60)
        return
    
    if not description:
        print("错误: 任务描述不能为空")
        return
    
    print(f"\n[1/8] 接收任务: {description}")
    
    # 2. 创建任务
    task = task_manager.create_task(description)
    task.update_status(TASK_STATUS_NEW)
    audit_logger.log("task_created", {
        "task_id": task.task_id,
        "description": description,
        "status": task.status,
    })
    print(f"[2/8] 任务已创建: {task.task_id}")
    
    # 3. Context Engine 构建上下文
    print("[3/8] 构建上下文...")
    openmemory_results = await search_openmemory(description, top_k=3)
    context = build_context(task, openmemory_results=openmemory_results)
    task.context = context
    task.update_status(TASK_STATUS_CONTEXT_BUILT)
    task_manager.update_task(task)  # 保存快照
    audit_logger.log("context_built", {
        "task_id": task.task_id,
        "openmemory_results_count": len(openmemory_results),
    })
    print(f"  - 身份配置已加载")
    print(f"  - OpenMemory 搜索结果: {len(openmemory_results)} 条")
    
    def _risk_rank(value: str) -> int:
        rank_map = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}
        return rank_map.get((value or "").upper(), 2)

    def _enforce_min_risk(plan, min_risk: str) -> None:
        if not min_risk:
            return
        min_rank = _risk_rank(min_risk)
        for step in plan.steps:
            if _risk_rank(step.risk_level) < min_rank:
                step.risk_level = min_risk

    def _load_skill_fulltext(skill_id: str) -> str:
        # 根据渐进式加载原则：只加载 SKILL.md，不自动加载引用文件
        # LLM 可以根据 SKILL.md 中的提示，在需要时通过文件工具读取引用文件
        fulltext = skills_registry.load_skill_fulltext(skill_id, include_references=False)
        audit_logger.log("skill.loaded", {
            "skill_id": skill_id,
            "bytes_loaded": len(fulltext.encode("utf-8")),
            "progressive_disclosure": True,  # 标记使用了渐进式加载
        })
        return fulltext

    # 4. Router 路由
    print("[4/8] 路由任务...")
    available_tools = tool_registry.list_all()
    available_skills = skills_registry.list_all()
    llm_client = None
    llm_router_enabled = os.getenv("LLM_ENABLE_ROUTER") == "1"
    llm_planner_enabled = os.getenv("LLM_ENABLE_PLANNER") == "1"
    if llm_router_enabled or llm_planner_enabled:
        llm_client = build_llm_client()
        if llm_client is None:
            llm_router_enabled = False
            llm_planner_enabled = False

    route_decision = None
    matched_skill = None
    routed_tools = []
    skill_fulltext = ""
    use_planner_for_skill = False

    if llm_router_enabled and llm_client:
        capability_index = build_capability_index(skills_registry, tool_registry)
        route_decision = route_llm_first(
            task.description,
            context,
            capability_index,
            llm_client,
            audit_logger=audit_logger,
        )

        if route_decision.get("fallback_to_rule"):
            matched_skill, routed_tools = route_task(task, available_tools, available_skills)
        else:
            route_type = route_decision.get("route_type")
            if route_type == "skill":
                skill_id = route_decision.get("skill_id")
                matched_skill = available_skills.get(skill_id)
                if not matched_skill:
                    matched_skill, routed_tools = route_task(task, available_tools, available_skills)
                else:
                    skill_fulltext = _load_skill_fulltext(matched_skill.skill_id)
                    # 如果启用了 LLM planner，使用 LLM 来生成计划（能理解技能文档并生成实际内容）
                    # 否则使用 skill_to_plan（解析执行步骤但只能生成占位文件）
                    use_planner_for_skill = llm_planner_enabled
            elif route_type in ("tool", "mcp"):
                tool_ids = route_decision.get("tool_ids") or []
                routed_tools = [
                    tool_id
                    for tool_id in tool_ids
                    if tool_id in available_tools or (isinstance(tool_id, str) and tool_id.startswith("mcp."))
                ]
                if not routed_tools:
                    matched_skill, routed_tools = route_task(task, available_tools, available_skills)
            elif route_type == "qa":
                print("\n进入问答模式，不进入规划与执行。")
                answer = handle_qa(
                    task.description,
                    context,
                    llm_client,
                    audit_logger=audit_logger,
                )
                task.update_status(TASK_STATUS_COMPLETED)
                task_manager.update_task(task, extra_info={"qa_answer": answer})
                audit_logger.log("task_completed", {
                    "task_id": task.task_id,
                    "qa": True,
                })
                print(f"\n回答:\n{answer}")
                return
            elif route_type == "clarify":
                print("\n需要澄清，不进入规划与执行。")
                questions = route_decision.get("clarify_questions") or []
                if questions:
                    print("澄清问题：")
                    for q in questions:
                        print(f"- {q}")
                return
            else:
                matched_skill, routed_tools = route_task(task, available_tools, available_skills)
    else:
        matched_skill, routed_tools = route_task(task, available_tools, available_skills)
    
    if matched_skill:
        print(f"  - 匹配到技能: {matched_skill.name} ({matched_skill.skill_id})")
        print(f"  - 技能描述: {matched_skill.description}")
    else:
        print(f"  - 路由到工具: {', '.join(routed_tools)}")
    
    # 5. Planner 生成计划
    print("[5/8] 生成执行计划...")
    if matched_skill:
        if not skill_fulltext:
            skill_fulltext = _load_skill_fulltext(matched_skill.skill_id)
        # 如果启用了 LLM planner，优先使用 LLM 来生成计划（能理解技能文档并生成实际内容）
        # 否则使用 skill_to_plan（解析执行步骤但只能生成占位文件）
        if llm_planner_enabled and llm_client:
            plan = await planner.create_plan(
                task,
                available_tools,
                routed_tools,
                skill_fulltext=skill_fulltext,
                llm_client=llm_client,
                audit_logger=audit_logger,
            )
            plan.source = f"skill:{matched_skill.skill_id}"
        else:
            # 使用技能生成计划（保持兼容）
            if skill_fulltext:
                matched_skill.instructions_md = skill_fulltext
            plan = skill_to_plan(matched_skill, task.task_id, sandbox_root)
            plan.source = f"skill:{matched_skill.skill_id}"
    else:
        # 使用默认 Planner
        plan = await planner.create_plan(
            task,
            available_tools,
            routed_tools,
            llm_client=llm_client if llm_planner_enabled else None,
            audit_logger=audit_logger,
        )

    if route_decision:
        _enforce_min_risk(plan, route_decision.get("min_risk"))
    
    task.update_status(TASK_STATUS_PLANNED)
    # 保存快照（包含 plan 和 skill_id）
    task_manager.update_task(task, extra_info={
        "plan": plan,
        "skill_id": matched_skill.skill_id if matched_skill else None,
        "routed_tools": routed_tools,
    })
    audit_logger.log("plan_created", {
        "task_id": task.task_id,
        "plan_id": plan.plan_id,
        "steps_count": len(plan.steps),
        "source": plan.source,
    })
    print(f"  - 计划ID: {plan.plan_id}")
    print(f"  - 计划来源: {plan.source or 'planner'}")
    print(f"  - 步骤数: {len(plan.steps)}")
    for i, step in enumerate(plan.steps, 1):
        print(f"    {i}. {step.tool_id} - {step.description} (风险: {step.risk_level})")
    
    # 6. Risk Gate 风险评估
    print("[6/8] 风险评估...")
    risk_assessment = approval_gate.assess_plan_risk(plan.steps)
    print(f"  - 风险等级: {risk_assessment.risk_level}")
    print(f"  - 需要审批: {risk_assessment.requires_approval}")
    
    approval = None
    if risk_assessment.is_approval_required():
        task.update_status(TASK_STATUS_WAITING_APPROVAL)
        task_manager.update_task(task, extra_info={"plan": plan})  # 保存快照
        audit_logger.log("waiting_approval", {
            "task_id": task.task_id,
            "risk_level": risk_assessment.risk_level,
            "reason": risk_assessment.reason,
        })
        
        # CLI 用户审批
        while True:
            user_input = input(f"\n⚠️  检测到风险等级 {risk_assessment.risk_level}，需要审批。是否批准执行? (yes/no): ").strip().lower()
            if user_input in ("yes", "y"):
                approval = approval_gate.approve(task.task_id, approved=True, approver="user")
                task.update_status(TASK_STATUS_APPROVED)
                task_manager.update_task(task, extra_info={"plan": plan, "approval": approval})  # 保存快照
                audit_logger.log("task_approved", {
                    "approval_id": approval.approval_id,
                    "task_id": task.task_id,
                    "approver": approval.approver,
                })
                print("✓ 已批准")
                break
            elif user_input in ("no", "n"):
                approval = approval_gate.approve(task.task_id, approved=False, approver="user")
                task_manager.update_task(task, extra_info={"plan": plan, "approval": approval})  # 保存快照
                audit_logger.log("task_rejected", {
                    "approval_id": approval.approval_id,
                    "task_id": task.task_id,
                    "approver": approval.approver,
                })
                print("✗ 已拒绝，任务终止")
                return
            else:
                print("请输入 yes 或 no")
    else:
        # 自动批准低风险任务
        approval = approval_gate.approve(task.task_id, approved=True, approver="system")
        task.update_status(TASK_STATUS_APPROVED)
        task_manager.update_task(task, extra_info={"plan": plan, "approval": approval})  # 保存快照
        audit_logger.log("task_auto_approved", {
            "approval_id": approval.approval_id,
            "task_id": task.task_id,
            "risk_level": risk_assessment.risk_level,
        })
        print("  - 自动批准（低风险）")
    
    # 7. 执行工具
    print("\n[7/8] 执行工具...")
    task.update_status(TASK_STATUS_RUNNING)
    audit_logger.log("task_started", {"task_id": task.task_id})
    
    executed_tools = []
    for i, step in enumerate(plan.steps, 1):
        print(f"\n  步骤 {i}/{len(plan.steps)}: {step.tool_id}")
        print(f"    描述: {step.description}")
        
        tool = tool_registry.get(step.tool_id)
        if not tool:
            if step.tool_id.startswith("mcp."):
                print(f"    ✗ 错误: {step.tool_id} 未接入 MCP client")
                tool_result = tool_runner.run_missing_mcp(step.tool_id, step.step_id)
                audit_logger.log("mcp.missing_client", {
                    "task_id": task.task_id,
                    "step_id": step.step_id,
                    "tool_id": step.tool_id,
                })
            else:
                print(f"    ✗ 错误: 工具 {step.tool_id} 未找到")
                continue
        else:
            # 执行工具
            tool_result = await tool_runner.run(tool, step.step_id, step.params)
        
        if tool_result.success:
            print(f"    ✓ 执行成功")
            executed_tools.append(step.tool_id)
            
            # 记录动作
            task.add_action({
                "step_id": step.step_id,
                "tool_id": step.tool_id,
                "description": step.description,
                "success": True,
                "result": tool_result.result,
            })
            
            # 收集产物
            if tool_result.evidence_refs:
                for ref in tool_result.evidence_refs:
                    task.add_artifact(ref)
                    print(f"    📄 产物: {ref}")
            
            # 特殊处理：python_run 工具的审计日志
            if step.tool_id == "python_run":
                result = tool_result.result
                meta = result.get("meta", {})
                audit_logger.log("tool.python_run", {
                    "task_id": task.task_id,
                    "step_id": step.step_id,
                    "script_path_relative": meta.get("script_path", ""),
                    "args": meta.get("args", []),
                    "cwd": meta.get("cwd", str(sandbox_root)),
                    "timeout_seconds": meta.get("timeout_seconds", 60),
                    "exit_code": result.get("exit_code", -1),
                    "stdout_len": len(result.get("stdout_excerpt", "")),
                    "stderr_len": len(result.get("stderr_excerpt", "")),
                    "duration_ms": meta.get("duration_ms", 0),
                })
            else:
                audit_logger.log("tool_executed", {
                    "task_id": task.task_id,
                    "step_id": step.step_id,
                    "tool_id": step.tool_id,
                    "success": True,
                    "evidence_refs": tool_result.evidence_refs,
                })
        else:
            print(f"    ✗ 执行失败: {tool_result.error}")
            task.add_action({
                "step_id": step.step_id,
                "tool_id": step.tool_id,
                "description": step.description,
                "success": False,
                "error": tool_result.error,
            })
            audit_logger.log("tool_executed", {
                "task_id": task.task_id,
                "step_id": step.step_id,
                "tool_id": step.tool_id,
                "success": False,
                "error": tool_result.error,
            })
    
    # 8. 任务完成
    task.update_status(TASK_STATUS_COMPLETED)
    # 保存最终快照（包含完整信息）
    task_manager.update_task(task, extra_info={
        "plan": plan,
        "skill_id": matched_skill.skill_id if matched_skill else None,
        "routed_tools": routed_tools,
        "approval": approval,
    })
    audit_logger.log("task_completed", {
        "task_id": task.task_id,
        "artifacts": task.artifacts,
        "executed_tools": executed_tools,
    })
    
    # 输出总结
    print("\n" + "=" * 60)
    print("[8/8] 任务完成总结")
    print("=" * 60)
    print(f"任务ID: {task.task_id}")
    print(f"状态: {task.status}")
    print(f"执行的工具: {', '.join(executed_tools) if executed_tools else '无'}")
    print(f"产物路径:")
    if task.artifacts:
        for artifact in task.artifacts:
            print(f"  - {artifact}")
    else:
        print("  - 无")
    print(f"审批记录: {approval.approval_id if approval else '无'}")
    print(f"审计日志: memory/raw_logs/audit.log.jsonl")
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
