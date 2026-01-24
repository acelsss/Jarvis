"""Prompt validation utilities."""
import re
from typing import List, Dict, Any, Set
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def _parse_frontmatter_minimal(text: str) -> tuple[Dict[str, Any], str]:
    """最小化解析 YAML frontmatter（不依赖 yaml 库）。
    
    Args:
        text: 完整 prompt 文本
        
    Returns:
        (frontmatter_dict, content) 元组
    """
    if not text.startswith("---"):
        return {}, text
    
    # 找到第二个 "---"
    second_dash = text.find("\n---", 4)
    if second_dash == -1:
        return {}, text
    
    frontmatter_text = text[4:second_dash].strip()
    content = text[second_dash + 5:].strip()
    
    # 最小化解析：读取 key: value 对
    frontmatter = {}
    for line in frontmatter_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            # 处理列表项（以 - 开头）
            if key.startswith("-"):
                # 这是列表项，需要特殊处理
                continue
            # 处理简单值
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            frontmatter[key] = value
    
    return frontmatter, content


def _parse_frontmatter_yaml(text: str) -> tuple[Dict[str, Any], str]:
    """使用 yaml 库解析 frontmatter。
    
    Args:
        text: 完整 prompt 文本
        
    Returns:
        (frontmatter_dict, content) 元组
    """
    if not HAS_YAML:
        return _parse_frontmatter_minimal(text)
    
    if not text.startswith("---"):
        return {}, text
    
    second_dash = text.find("\n---", 4)
    if second_dash == -1:
        return {}, text
    
    frontmatter_text = text[4:second_dash].strip()
    content = text[second_dash + 5:].strip()
    
    try:
        frontmatter = yaml.safe_load(frontmatter_text) or {}
        if not isinstance(frontmatter, dict):
            return {}, text
        return frontmatter, content
    except Exception:
        # 如果 yaml 解析失败，回退到最小解析
        return _parse_frontmatter_minimal(text)


def _extract_variables(text: str) -> Set[str]:
    """提取文本中所有的 {{var}} 变量。
    
    Args:
        text: prompt 内容文本
        
    Returns:
        变量名集合
    """
    pattern = r"\{\{(\w+)\}\}"
    matches = re.findall(pattern, text)
    return set(matches)


def _extract_inputs_declaration(frontmatter: Dict[str, Any]) -> Set[str]:
    """从 frontmatter 中提取 inputs 声明的变量名。
    
    Args:
        frontmatter: frontmatter 字典
        
    Returns:
        变量名集合
    """
    inputs = frontmatter.get("inputs", [])
    if not isinstance(inputs, list):
        return set()
    
    variables = set()
    for item in inputs:
        if isinstance(item, str):
            # 格式: "var_name: description"
            if ":" in item:
                var_name = item.split(":")[0].strip()
                variables.add(var_name)
        elif isinstance(item, dict):
            # 格式: {"var_name": "description"} 或 {"var_name": {"type": "...", "description": "..."}}
            variables.update(item.keys())
    
    return variables


def validate_prompt_text(prompt_id: str, raw_text: str) -> List[str]:
    """验证 prompt 文本是否符合规范。
    
    Args:
        prompt_id: prompt 标识符（文件路径，不含 .md）
        raw_text: prompt 文件的原始文本
        
    Returns:
        错误列表，如果为空则表示验证通过
    """
    errors: List[str] = []
    
    # 1. 检查 frontmatter 存在
    if not raw_text.startswith("---"):
        errors.append(f"{prompt_id}: 缺少 YAML frontmatter（必须以 '---' 开头）")
        return errors  # 如果没有 frontmatter，无法继续验证
    
    # 2. 解析 frontmatter
    frontmatter, content = _parse_frontmatter_yaml(raw_text)
    
    if not frontmatter:
        errors.append(f"{prompt_id}: YAML frontmatter 解析失败或为空")
        return errors
    
    # 3. 检查必需字段
    required_fields = ["id", "name", "version", "used_by", "inputs", "output"]
    for field in required_fields:
        if field not in frontmatter:
            errors.append(f"{prompt_id}: frontmatter 缺少必需字段: {field}")
    
    # 4. 检查 output.type
    output = frontmatter.get("output", {})
    if isinstance(output, dict):
        output_type = output.get("type")
        if output_type not in ["json", "text"]:
            errors.append(f"{prompt_id}: output.type 必须是 'json' 或 'text'，当前为: {output_type}")
    else:
        errors.append(f"{prompt_id}: output 必须是字典类型")
    
    # 5. 检查是否包含 ## system 分段
    if "## system" not in content:
        errors.append(f"{prompt_id}: 缺少必需的 '## system' 分段")
    
    # 6. 检查变量声明
    variables_in_text = _extract_variables(content)
    variables_declared = _extract_inputs_declaration(frontmatter)
    
    # 检查所有使用的变量是否都已声明
    undeclared = variables_in_text - variables_declared
    if undeclared:
        errors.append(
            f"{prompt_id}: 使用了未声明的变量: {', '.join(sorted(undeclared))}。"
            f"请在 frontmatter.inputs 中声明这些变量。"
        )
    
    return errors
