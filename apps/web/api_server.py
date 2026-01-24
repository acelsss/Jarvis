"""Jarvis Web API Server"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Any, Dict, List
from datetime import datetime
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager

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
from core.session.history import SessionHistoryBuffer

# 全局状态
task_manager: Optional[TaskManager] = None
planner: Optional[Planner] = None
approval_gate: Optional[ApprovalGate] = None
executor: Optional[Executor] = None
audit_logger: Optional[AuditLogger] = None
tool_registry: Optional[ToolRegistry] = None
tool_runner: Optional[ToolRunner] = None
skills_registry: Optional[SkillsRegistry] = None
sandbox_root: str = "./sandbox"
llm_client: Any = None
llm_router_enabled: bool = False
llm_planner_enabled: bool = False
session_history: Optional[SessionHistoryBuffer] = None
active_connections: List[WebSocket] = []


class TaskRequest(BaseModel):
    description: str


class ApprovalRequest(BaseModel):
    task_id: str
    approved: bool


async def broadcast_message(message: Dict):
    """向所有连接的WebSocket客户端广播消息"""
    if not active_connections:
        return
    
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            disconnected.append(connection)
    
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


async def process_task_with_updates(
    description: str,
    websocket: Optional[WebSocket] = None
) -> Dict:
    """处理任务并发送实时更新"""
    global task_manager, planner, approval_gate, executor, audit_logger
    global tool_registry, tool_runner, skills_registry, session_history
    global llm_client, llm_router_enabled, llm_planner_enabled
    
    async def send_update(stage: str, data: Dict):
        update = {
            "type": "task_update",
            "stage": stage,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        if websocket:
            try:
                await websocket.send_json(update)
            except Exception:
                pass  # WebSocket可能已断开，继续广播给其他连接
        await broadcast_message(update)
    
    try:
        # 记录用户输入
        session_history.add_user(description)
        chat_history_messages = session_history.get_window()
        
        await send_update("received", {"description": description})
        
        # 创建任务
        task = task_manager.create_task(description)
        task.update_status(TASK_STATUS_NEW)
        audit_logger.log("task_created", {
            "task_id": task.task_id,
            "description": description,
            "status": task.status,
        })
        await send_update("task_created", {
            "task_id": task.task_id,
            "status": task.status
        })
        
        # 构建上下文
        await send_update("building_context", {})
        openmemory_results = await search_openmemory(description, top_k=3)
        context = build_context(task, openmemory_results=openmemory_results)
        task.context = context
        task.update_status(TASK_STATUS_CONTEXT_BUILT)
        task_manager.update_task(task)
        audit_logger.log("context_built", {
            "task_id": task.task_id,
            "openmemory_results_count": len(openmemory_results),
        })
        await send_update("context_built", {
            "openmemory_results_count": len(openmemory_results)
        })
        
        # 路由
        await send_update("routing", {})
        available_tools = tool_registry.list_all()
        available_skills = skills_registry.list_all()
        
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
                chat_history_messages=chat_history_messages,
            )
            
            if route_decision.get("fallback_to_rule"):
                matched_skill, routed_tools = route_task(
                    task, available_tools, available_skills,
                    llm_client=llm_client,
                    audit_logger=audit_logger,
                    chat_history_messages=chat_history_messages,
                )
            else:
                route_type = route_decision.get("route_type")
                if route_type == "skill":
                    skill_id = route_decision.get("skill_id")
                    matched_skill = available_skills.get(skill_id)
                    if matched_skill:
                        skill_fulltext = skills_registry.load_skill_fulltext(
                            matched_skill.skill_id, include_references=False
                        )
                        use_planner_for_skill = llm_planner_enabled
                elif route_type == "qa":
                    answer = handle_qa(
                        task.description,
                        context,
                        llm_client,
                        audit_logger=audit_logger,
                        chat_history_messages=chat_history_messages,
                    )
                    task.update_status(TASK_STATUS_COMPLETED)
                    task_manager.update_task(task, extra_info={"qa_answer": answer})
                    session_history.add_assistant(answer)
                    await send_update("completed", {
                        "task_id": task.task_id,
                        "answer": answer,
                        "qa": True
                    })
                    return {
                        "task_id": task.task_id,
                        "status": "completed",
                        "answer": answer,
                        "qa": True
                    }
        else:
            matched_skill, routed_tools = route_task(
                task, available_tools, available_skills,
                llm_client=llm_client,
                audit_logger=audit_logger,
                chat_history_messages=chat_history_messages,
            )
        
        route_info = {}
        if matched_skill:
            route_info = {
                "type": "skill",
                "skill_id": matched_skill.skill_id,
                "skill_name": matched_skill.name
            }
        else:
            route_info = {
                "type": "tools",
                "tools": routed_tools
            }
        await send_update("routed", route_info)
        
        # 生成计划
        await send_update("planning", {})
        if matched_skill:
            if not skill_fulltext:
                skill_fulltext = skills_registry.load_skill_fulltext(
                    matched_skill.skill_id, include_references=False
                )
                # 更新技能的instructions_md
                matched_skill.instructions_md = skill_fulltext
            
            if use_planner_for_skill and llm_client:
                plan = await planner.create_plan(
                    task,
                    available_tools,
                    routed_tools,
                    skill_fulltext=skill_fulltext,
                    llm_client=llm_client,
                    audit_logger=audit_logger,
                    chat_history_messages=chat_history_messages,
                )
                plan.source = f"skill:{matched_skill.skill_id}"
            else:
                plan = skill_to_plan(matched_skill, task.task_id, sandbox_root)
                plan.source = f"skill:{matched_skill.skill_id}"
        else:
            if not routed_tools:
                raise ValueError("没有可用的工具或技能来处理此任务")
            plan = await planner.create_plan(
                task,
                available_tools,
                routed_tools,
                llm_client=llm_client,
                audit_logger=audit_logger,
                chat_history_messages=chat_history_messages,
            )
        
        if not plan:
            raise ValueError("计划生成失败")
        
        task.plan = plan
        task.update_status(TASK_STATUS_PLANNED)
        task_manager.update_task(task)
        
        if not plan.steps:
            raise ValueError("计划中没有执行步骤")
        
        plan_steps = [
            {
                "step_id": step.step_id,
                "description": step.description,
                "tool_id": step.tool_id,
                "risk_level": step.risk_level
            }
            for step in plan.steps
        ]
        await send_update("planned", {"steps": plan_steps})
        
        # 风险评估
        if plan.steps:
            max_risk = max([step.risk_level for step in plan.steps], key=lambda r: {"R0": 0, "R1": 1, "R2": 2, "R3": 3}.get(r, 2))
        else:
            max_risk = "R0"
        needs_approval = max_risk in ("R2", "R3")
        
        if needs_approval:
            task.update_status(TASK_STATUS_WAITING_APPROVAL)
            task_manager.update_task(task)
            await send_update("waiting_approval", {
                "task_id": task.task_id,
                "max_risk": max_risk,
                "steps": plan_steps
            })
            return {
                "task_id": task.task_id,
                "status": "waiting_approval",
                "max_risk": max_risk,
                "steps": plan_steps
            }
        
        # 执行
        task.update_status(TASK_STATUS_APPROVED)
        task.update_status(TASK_STATUS_RUNNING)
        task_manager.update_task(task)
        await send_update("executing", {})
        
        execution_result = await executor.execute(
            task, plan, tool_registry, tool_runner, audit_logger
        )
        
        task.update_status(TASK_STATUS_COMPLETED)
        task_manager.update_task(task)
        
        artifacts = [
            {
                "path": art.path,
                "type": art.type,
                "description": art.description
            }
            for art in (execution_result.artifacts or [])
        ]
        
        await send_update("completed", {
            "task_id": task.task_id,
            "artifacts": artifacts,
            "summary": execution_result.summary
        })
        
        session_history.add_assistant(execution_result.summary or "任务已完成")
        
        return {
            "task_id": task.task_id,
            "status": "completed",
            "artifacts": artifacts,
            "summary": execution_result.summary
        }
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_trace = traceback.format_exc()
        print(f"处理任务时出错: {error_msg}")
        print(error_trace)
        
        try:
            await send_update("error", {"message": error_msg})
        except Exception:
            pass  # 如果发送更新失败，继续抛出原始错误
        
        raise HTTPException(status_code=500, detail=error_msg)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global task_manager, planner, approval_gate, executor, audit_logger
    global tool_registry, tool_runner, skills_registry, session_history
    global llm_client, llm_router_enabled, llm_planner_enabled, sandbox_root
    
    # 启动时初始化
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
    
    skills_registry = SkillsRegistry(workspace_dir="./skills_workspace")
    skills_registry.scan_workspace()
    
    file_tool = FileTool(sandbox_root=sandbox_root)
    shell_tool = ShellTool()
    python_run_tool = PythonRunTool()
    tool_registry.register(file_tool)
    tool_registry.register(shell_tool)
    tool_registry.register(python_run_tool)
    
    llm_router_enabled = os.getenv("LLM_ENABLE_ROUTER") == "1"
    llm_planner_enabled = os.getenv("LLM_ENABLE_PLANNER") == "1"
    if llm_router_enabled or llm_planner_enabled:
        llm_client = build_llm_client()
        if llm_client is None:
            llm_router_enabled = False
            llm_planner_enabled = False
    
    session_history = SessionHistoryBuffer()
    
    yield
    
    # 关闭时清理
    pass


app = FastAPI(title="Jarvis API", lifespan=lifespan)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """返回前端页面"""
    frontend_path = project_root / "apps" / "web" / "frontend" / "index.html"
    if frontend_path.exists():
        html_content = frontend_path.read_text(encoding="utf-8")
        return HTMLResponse(content=html_content)
    return {"message": "Jarvis API Server", "version": "0.1.0"}


@app.post("/api/tasks")
async def create_task(request: TaskRequest):
    """创建并处理任务"""
    try:
        result = await process_task_with_updates(request.description)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/tasks/{task_id}/approve")
async def approve_task(task_id: str, request: ApprovalRequest):
    """审批任务"""
    global task_manager, executor, tool_registry, tool_runner, audit_logger
    
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if request.approved:
        task.update_status(TASK_STATUS_APPROVED)
        task.update_status(TASK_STATUS_RUNNING)
        task_manager.update_task(task)
        
        execution_result = await executor.execute(
            task, task.plan, tool_registry, tool_runner, audit_logger
        )
        
        task.update_status(TASK_STATUS_COMPLETED)
        task_manager.update_task(task)
        
        artifacts = [
            {
                "path": art.path,
                "type": art.type,
                "description": art.description
            }
            for art in (execution_result.artifacts or [])
        ]
        
        await broadcast_message({
            "type": "task_update",
            "stage": "completed",
            "data": {
                "task_id": task_id,
                "artifacts": artifacts,
                "summary": execution_result.summary
            },
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "task_id": task_id,
            "status": "completed",
            "artifacts": artifacts,
            "summary": execution_result.summary
        }
    else:
        task.update_status(TASK_STATUS_COMPLETED)
        task_manager.update_task(task, extra_info={"approved": False})
        await broadcast_message({
            "type": "task_update",
            "stage": "cancelled",
            "data": {"task_id": task_id},
            "timestamp": datetime.now().isoformat()
        })
        return {"task_id": task_id, "status": "cancelled"}


@app.get("/api/tasks")
async def list_tasks():
    """列出所有任务"""
    global task_manager
    # 这里需要实现任务列表功能
    return {"tasks": []}


@app.get("/api/skills")
async def list_skills():
    """列出所有可用技能"""
    global skills_registry
    skills = skills_registry.list_all()
    return {
        "skills": [
            {
                "skill_id": skill.skill_id,
                "name": skill.name,
                "description": skill.description
            }
            for skill in skills.values()
        ]
    }


@app.get("/api/tools")
async def list_tools():
    """列出所有可用工具"""
    global tool_registry
    tools = tool_registry.list_all()
    return {
        "tools": [
            {
                "tool_id": tool.tool_id,
                "name": tool.name,
                "description": tool.description
            }
            for tool in tools.values()
        ]
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接端点"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            # 可以处理客户端发送的消息
            message = json.loads(data)
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        active_connections.remove(websocket)


# 静态文件服务
frontend_dir = project_root / "apps" / "web" / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
