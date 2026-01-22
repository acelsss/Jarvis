"""Plan conversion utilities."""
import re
import warnings
import json
from typing import List, Dict, Any

from core.contracts.skill import Plan, PlanStep, JarvisSkill
from core.contracts.risk import RISK_LEVEL_R1
from core.utils.ids import generate_id


def _make_json_safe(value: Any) -> Any:
    """将值转换为 JSON-safe 类型。
    
    Args:
        value: 要转换的值
        
    Returns:
        JSON-safe 的值（dict/list/str/int/float/bool/None）
    """
    if value is None:
        return None
    elif isinstance(value, (str, int, float, bool)):
        return value
    elif isinstance(value, dict):
        return {k: _make_json_safe(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [_make_json_safe(item) for item in value]
    else:
        # 对于其他类型，尝试转换为字符串
        try:
            # 先尝试 JSON 序列化测试
            json.dumps(value)
            return value
        except (TypeError, ValueError):
            # 如果无法序列化，转换为字符串并记录警告
            warnings.warn(
                f"Value of type {type(value).__name__} cannot be JSON-serialized, "
                f"converting to string: {str(value)[:100]}",
                UserWarning
            )
            return str(value)


def step_to_dict(step: PlanStep) -> Dict[str, Any]:
    """将 PlanStep 转换为字典（JSON-safe）。
    
    Args:
        step: PlanStep 对象
        
    Returns:
        包含所有字段的字典
    """
    step_dict = {
        "step_id": step.step_id,
        "tool_id": step.tool_id,
        "description": step.description,
        "risk_level": step.risk_level,
    }
    
    # 处理 params，确保 JSON-safe
    if step.params is not None:
        step_dict["params"] = _make_json_safe(step.params)
    else:
        step_dict["params"] = {}
    
    return step_dict


def plan_to_dict(plan: Plan) -> Dict[str, Any]:
    """将计划转换为字典（JSON-safe）。
    
    Args:
        plan: Plan 对象
        
    Returns:
        纯 dict/list/str/int/bool/None 结构的字典
    """
    return {
        "plan_id": plan.plan_id,
        "steps": [step_to_dict(step) for step in plan.steps],
        "estimated_duration": plan.estimated_duration,
        "source": plan.source,
    }


def dict_to_plan(data: Dict[str, Any]) -> Plan:
    """从字典创建计划。"""
    return Plan(
        plan_id=data["plan_id"],
        steps=data["steps"],
        estimated_duration=data.get("estimated_duration"),
        source=data.get("source"),
    )


def skill_to_plan(jarvis_skill: JarvisSkill, task_id: str, sandbox_root: str = "./sandbox") -> Plan:
    """将 JarvisSkill 的 instructions_md 转换为 Task plan。
    
    解析技能文档中的"执行步骤"部分，生成实际的执行计划。
    如果没有找到"执行步骤"，则回退到简单模板。
    
    Args:
        jarvis_skill: JarvisSkill 对象
        task_id: 任务ID
        sandbox_root: 沙箱根目录
        
    Returns:
        执行计划
    """
    plan_id = generate_id("plan")
    steps: List[PlanStep] = []
    
    instructions = jarvis_skill.instructions_md
    
    # 尝试解析"执行步骤"部分
    execution_steps_match = re.search(
        r'##\s*执行步骤\s*\n(.*?)(?=\n##|\Z)',
        instructions,
        re.DOTALL | re.IGNORECASE
    )
    
    if execution_steps_match:
        execution_steps_text = execution_steps_match.group(1).strip()
        # 解析编号列表（1. 2. 3. 等）
        step_lines = re.findall(r'^\d+\.\s*(.+)$', execution_steps_text, re.MULTILINE)
        
        if step_lines:
            # 根据执行步骤生成计划
            for i, step_desc in enumerate(step_lines, 1):
                # 检查步骤描述，确定使用什么工具
                step_desc_lower = step_desc.lower()
                
                # 判断步骤类型
                if "保存" in step_desc or "文件" in step_desc or "markdown" in step_desc_lower or "json" in step_desc_lower:
                    # 文件保存步骤
                    if "元数据" in step_desc or "meta" in step_desc_lower:
                        file_path = f"{sandbox_root}/{task_id}_article_meta.json"
                        file_content = json.dumps({
                            "task_id": task_id,
                            "skill_id": jarvis_skill.skill_id,
                            "title": "",
                            "summary": "",
                            "word_count": 0,
                            "created_at": ""
                        }, ensure_ascii=False, indent=2)
                    else:
                        file_path = f"{sandbox_root}/{task_id}_article.md"
                        file_content = f"# 文章标题\n\n## 摘要\n\n## 正文\n\n## 结尾\n\n---\n任务ID: {task_id}\n技能: {jarvis_skill.name}"
                    
                    step = PlanStep(
                        step_id=generate_id("step"),
                        tool_id="file",
                        description=f"{jarvis_skill.name} - {step_desc}",
                        params={
                            "operation": "write",
                            "path": file_path,
                            "content": file_content,
                        },
                        risk_level=RISK_LEVEL_R1,
                    )
                else:
                    # 其他步骤（分析、生成等），创建占位文件
                    # 注意：这些步骤实际上需要 LLM 来执行，这里只是创建占位
                    step = PlanStep(
                        step_id=generate_id("step"),
                        tool_id="file",
                        description=f"{jarvis_skill.name} - {step_desc}",
                        params={
                            "operation": "write",
                            "path": f"{sandbox_root}/{task_id}_skill_{jarvis_skill.skill_id}_step{i}.md",
                            "content": f"# {step_desc}\n\n**注意**: 此步骤需要 LLM 支持才能执行。\n\n任务ID: {task_id}\n技能: {jarvis_skill.name}",
                        },
                        risk_level=RISK_LEVEL_R1,
                    )
                steps.append(step)
    
    # 如果没有找到执行步骤，回退到简单模板
    if not steps:
        # 创建最终产物文件
        final_step = PlanStep(
            step_id=generate_id("step"),
            tool_id="file",
            description=f"{jarvis_skill.name} - 生成最终产物",
            params={
                "operation": "write",
                "path": f"{sandbox_root}/{task_id}_article.md",
                "content": f"# {jarvis_skill.name}\n\n任务ID: {task_id}\n技能ID: {jarvis_skill.skill_id}\n\n**注意**: 此技能需要 LLM 支持才能生成实际内容。\n\n技能说明:\n{jarvis_skill.description}",
            },
            risk_level=RISK_LEVEL_R1,
        )
        steps.append(final_step)
    
    return Plan(
        plan_id=plan_id,
        steps=steps,
        estimated_duration=len(steps) * 10,
        source=f"skill:{jarvis_skill.skill_id}",
    )
