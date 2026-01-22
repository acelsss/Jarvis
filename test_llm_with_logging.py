#!/usr/bin/env python3
"""测试LLM路由和计划生成，并记录所有LLM交互。"""
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

# 加载.env文件
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加载 .env 文件: {env_path}")
    else:
        print(f"⚠️  .env 文件不存在: {env_path}")
except ImportError:
    print("⚠️  python-dotenv 未安装，跳过.env文件加载")

# 确保启用LLM
os.environ["LLM_ENABLE_ROUTER"] = "1"
os.environ["LLM_ENABLE_PLANNER"] = "1"

from core.llm.client_base import LLMClient
from core.llm.factory import build_llm_client
from core.contracts.task import Task, TASK_STATUS_NEW
from core.context_engine.build_context import build_context, search_openmemory
from core.router.route import route_llm_first
from core.orchestrator.planner import Planner
from core.capabilities.index_builder import build_capability_index
from tools.registry import ToolRegistry
from tools.local.file_tool import FileTool
from tools.local.shell_tool import ShellTool
from skills.registry import SkillsRegistry


class LoggingLLMClient:
    """带日志记录的LLM客户端包装器。"""
    
    def __init__(self, base_client: LLMClient):
        self.base_client = base_client
        self.call_count = 0
        self.calls = []
    
    def complete_json(
        self, purpose: str, system: str, user: str, schema_hint: str
    ) -> Dict:
        """调用LLM并记录请求和响应。"""
        self.call_count += 1
        call_id = self.call_count
        
        print("\n" + "=" * 80)
        print(f"LLM 调用 #{call_id} - {purpose.upper()}")
        print("=" * 80)
        
        # 记录请求
        print(f"\n[请求] Purpose: {purpose}")
        print(f"[请求] Schema Hint: {schema_hint[:100]}...")
        print(f"\n[System Prompt]:")
        print("-" * 80)
        print(system)
        print("-" * 80)
        
        print(f"\n[User Prompt]:")
        print("-" * 80)
        # 如果user太长，只显示前2000字符
        if len(user) > 2000:
            print(user[:2000])
            print(f"\n... (省略 {len(user) - 2000} 字符) ...")
        else:
            print(user)
        print("-" * 80)
        
        # 调用LLM
        print(f"\n[正在调用LLM...]")
        try:
            result = self.base_client.complete_json(
                purpose=purpose,
                system=system,
                user=user,
                schema_hint=schema_hint,
            )
            
            # 记录响应
            print(f"\n[响应] 成功")
            print(f"[响应] 类型: {type(result).__name__}")
            print(f"\n[响应内容]:")
            print("-" * 80)
            response_str = json.dumps(result, ensure_ascii=False, indent=2)
            print(response_str)
            print("-" * 80)
            
            # 保存调用记录
            self.calls.append({
                "call_id": call_id,
                "purpose": purpose,
                "timestamp": datetime.now().isoformat(),
                "system": system,
                "user": user,
                "schema_hint": schema_hint,
                "response": result,
            })
            
            return result
            
        except Exception as e:
            print(f"\n[响应] 错误: {e}")
            print(f"[响应] 异常类型: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            
            # 保存错误记录
            self.calls.append({
                "call_id": call_id,
                "purpose": purpose,
                "timestamp": datetime.now().isoformat(),
                "system": system,
                "user": user,
                "schema_hint": schema_hint,
                "error": str(e),
            })
            
            raise


async def test_skill_creator_with_llm():
    """测试skill-creator的LLM路由和计划生成。"""
    print("=" * 80)
    print("测试: Skill-Creator LLM 路由和计划生成")
    print("=" * 80)
    
    # 检查LLM配置
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if not provider:
        print("❌ 错误: LLM_PROVIDER 未设置")
        return False
    
    print(f"\n✅ LLM Provider: {provider}")
    
    # 构建基础LLM客户端
    base_client = build_llm_client()
    if base_client is None:
        print("❌ 错误: 无法构建LLM客户端，请检查配置")
        return False
    
    # 创建带日志的客户端
    llm_client = LoggingLLMClient(base_client)
    
    # 初始化组件
    skills_registry = SkillsRegistry(workspace_dir="./skills_workspace")
    skills_registry.scan_workspace()
    
    tool_registry = ToolRegistry()
    file_tool = FileTool(sandbox_root="./sandbox")
    shell_tool = ShellTool()
    tool_registry.register(file_tool)
    tool_registry.register(shell_tool)
    
    # 测试任务
    test_description = "我想创建一个新的skill，用于生成技术文档"
    print(f"\n📝 测试任务: {test_description}")
    
    # 创建任务
    from core.orchestrator.task_manager import TaskManager
    task_manager = TaskManager()
    task = task_manager.create_task(test_description)
    task.update_status(TASK_STATUS_NEW)
    
    # 构建上下文
    print("\n[1/4] 构建上下文...")
    openmemory_results = await search_openmemory(test_description, top_k=3)
    context = build_context(task, openmemory_results=openmemory_results)
    task.context = context
    print(f"✅ 上下文已构建 (OpenMemory结果: {len(openmemory_results)} 条)")
    
    # 路由任务
    print("\n[2/4] LLM 路由任务...")
    available_tools = tool_registry.list_all()
    available_skills = skills_registry.list_all()
    
    capability_index = build_capability_index(skills_registry, tool_registry)
    print(f"✅ 能力索引已构建 (技能: {len(capability_index.get('skills', []))}, 工具: {len(capability_index.get('tools', []))})")
    
    route_decision = route_llm_first(
        task.description,
        context,
        capability_index,
        llm_client,
        audit_logger=None,
    )
    
    print(f"\n✅ 路由决策:")
    print(f"   - 路由类型: {route_decision.get('route_type')}")
    print(f"   - 技能ID: {route_decision.get('skill_id')}")
    print(f"   - 置信度: {route_decision.get('confidence')}")
    print(f"   - 原因: {route_decision.get('reason')}")
    
    # 检查是否匹配到skill-creator
    matched_skill = None
    skill_fulltext = ""
    
    if route_decision.get("route_type") == "skill":
        skill_id = route_decision.get("skill_id")
        matched_skill = available_skills.get(skill_id)
        if matched_skill:
            print(f"\n✅ 匹配到技能: {matched_skill.name} ({skill_id})")
            # 根据渐进式加载原则：只加载 SKILL.md，不自动加载引用文件
            skill_fulltext = skills_registry.load_skill_fulltext(skill_id, include_references=False)
            print(f"✅ 技能主文件已加载 ({len(skill_fulltext)} 字符，符合渐进式加载原则)")
        else:
            print(f"\n⚠️  路由决策指向技能 {skill_id}，但未找到该技能")
    else:
        print(f"\n⚠️  路由决策类型为 {route_decision.get('route_type')}，不是skill")
    
    # 生成计划
    if matched_skill:
        print("\n[3/4] LLM 生成计划...")
        planner = Planner(sandbox_root="./sandbox")
        
        plan = await planner.create_plan(
            task,
            available_tools,
            [],
            skill_fulltext=skill_fulltext,
            llm_client=llm_client,
            audit_logger=None,
        )
        
        print(f"\n✅ 计划已生成:")
        print(f"   - 计划ID: {plan.plan_id}")
        print(f"   - 步骤数: {len(plan.steps)}")
        print(f"   - 来源: {plan.source}")
        
        print(f"\n计划步骤详情:")
        for i, step in enumerate(plan.steps, 1):
            print(f"\n   步骤 {i}:")
            print(f"     - 工具: {step.tool_id}")
            print(f"     - 描述: {step.description}")
            print(f"     - 风险: {step.risk_level}")
            if step.params:
                print(f"     - 参数: {json.dumps(step.params, ensure_ascii=False, indent=8)}")
    else:
        print("\n⚠️  未匹配到技能，跳过计划生成")
    
    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"✅ LLM 调用次数: {llm_client.call_count}")
    print(f"✅ 路由决策: {route_decision.get('route_type')}")
    if matched_skill:
        print(f"✅ 匹配技能: {matched_skill.name}")
        print(f"✅ 计划步骤数: {len(plan.steps) if 'plan' in locals() else 0}")
    else:
        print("⚠️  未匹配到skill-creator")
    
    # 保存调用记录
    log_file = Path("./llm_test_log.json")
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_description": test_description,
            "provider": provider,
            "total_calls": llm_client.call_count,
            "calls": llm_client.calls,
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ LLM调用记录已保存到: {log_file}")
    
    return matched_skill is not None and matched_skill.skill_id == "skill-creator"


def main():
    """主函数。"""
    import asyncio
    
    print("\n开始LLM测试...")
    print(f"LLM_PROVIDER: {os.getenv('LLM_PROVIDER', '未设置')}")
    print(f"LLM_ENABLE_ROUTER: {os.getenv('LLM_ENABLE_ROUTER', '0')}")
    print(f"LLM_ENABLE_PLANNER: {os.getenv('LLM_ENABLE_PLANNER', '0')}")
    
    try:
        success = asyncio.run(test_skill_creator_with_llm())
        if success:
            print("\n🎉 测试成功！skill-creator 被正确路由和计划生成。")
        else:
            print("\n⚠️  测试完成，但skill-creator未被匹配。")
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
