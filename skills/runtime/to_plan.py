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
    
    v0.1 简单模板：将 instructions 分段转换为 PlanStep，默认风险 R1。
    每个步骤都使用 file_tool 来保存中间结果。
    
    Args:
        jarvis_skill: JarvisSkill 对象
        task_id: 任务ID
        sandbox_root: 沙箱根目录
        
    Returns:
        执行计划
    """
    plan_id = generate_id("plan")
    steps: List[PlanStep] = []
    
    # 解析 instructions_md，按段落分割
    instructions = jarvis_skill.instructions_md
    
    # 按标题或空行分割段落
    # 匹配 Markdown 标题（# 开头）或空行分隔的段落
    paragraphs = re.split(r'\n\s*\n|\n(?=#)', instructions)
    
    # 过滤空段落
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    # 为每个段落创建一个步骤（最多5个步骤）
    for i, paragraph in enumerate(paragraphs[:5], 1):
        # 提取段落标题（如果有）
        title_match = re.match(r'^#+\s*(.+)$', paragraph, re.MULTILINE)
        if title_match:
            step_description = title_match.group(1)
            # 移除标题行
            content = re.sub(r'^#+\s*.+$', '', paragraph, flags=re.MULTILINE).strip()
        else:
            # 使用前50个字符作为描述
            step_description = paragraph[:50].replace('\n', ' ').strip()
            content = paragraph
        
        # 创建文件保存步骤内容
        step = PlanStep(
            step_id=generate_id("step"),
            tool_id="file",
            description=f"{jarvis_skill.name} - 步骤 {i}: {step_description}",
            params={
                "operation": "write",
                "path": f"{sandbox_root}/{task_id}_skill_{jarvis_skill.skill_id}_step{i}.md",
                "content": f"# {step_description}\n\n{content}\n\n---\n技能: {jarvis_skill.name}\n步骤: {i}/{len(paragraphs[:5])}",
            },
            risk_level=RISK_LEVEL_R1,
        )
        steps.append(step)
    
    # 如果步骤少于2个，至少创建一个总结文件
    if len(steps) < 2:
        summary_step = PlanStep(
            step_id=generate_id("step"),
            tool_id="file",
            description=f"{jarvis_skill.name} - 生成总结文件",
            params={
                "operation": "write",
                "path": f"{sandbox_root}/{task_id}_skill_{jarvis_skill.skill_id}_summary.md",
                "content": f"# {jarvis_skill.name}\n\n{jarvis_skill.description}\n\n## 执行说明\n\n{jarvis_skill.instructions_md}",
            },
            risk_level=RISK_LEVEL_R1,
        )
        steps.append(summary_step)
    
    # 创建最终产物文件
    final_step = PlanStep(
        step_id=generate_id("step"),
        tool_id="file",
        description=f"{jarvis_skill.name} - 生成最终产物",
        params={
            "operation": "write",
            "path": f"{sandbox_root}/{task_id}_skill_{jarvis_skill.skill_id}_final.md",
            "content": f"# {jarvis_skill.name}\n\n任务ID: {task_id}\n技能ID: {jarvis_skill.skill_id}\n\n## 完整内容\n\n{jarvis_skill.instructions_md}",
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
