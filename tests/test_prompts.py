"""Tests for prompt validation and loading."""
import os
from pathlib import Path
from typing import List

import pytest

from core.prompts.loader import PromptLoader
from core.prompts.validator import validate_prompt_text


def _get_all_prompt_files() -> List[Path]:
    """获取所有 prompt 文件路径。
    
    Returns:
        prompt 文件路径列表
    """
    project_root = Path(__file__).parent.parent
    prompts_dir = project_root / "prompts"
    
    if not prompts_dir.exists():
        return []
    
    prompt_files = []
    for md_file in prompts_dir.rglob("*.md"):
        # 跳过模板文件（可选）
        if md_file.name == "TEMPLATE.md":
            continue
        prompt_files.append(md_file)
    
    return sorted(prompt_files)


def _get_prompt_id(file_path: Path) -> str:
    """从文件路径生成 prompt_id。
    
    Args:
        file_path: prompt 文件路径
        
    Returns:
        prompt_id（相对于 prompts/ 目录的路径，不含 .md）
    """
    project_root = Path(__file__).parent.parent
    prompts_dir = project_root / "prompts"
    
    # 计算相对路径
    relative_path = file_path.relative_to(prompts_dir)
    # 去掉 .md 扩展名
    prompt_id = str(relative_path).replace(".md", "")
    return prompt_id


class TestPromptLoading:
    """测试 prompt 加载功能。"""
    
    def test_all_prompts_loadable(self):
        """测试所有 prompt 文件都能成功加载。"""
        loader = PromptLoader()
        prompt_files = _get_all_prompt_files()
        
        assert len(prompt_files) > 0, "未找到任何 prompt 文件"
        
        errors = []
        for prompt_file in prompt_files:
            prompt_id = _get_prompt_id(prompt_file)
            try:
                prompt_text = loader.load(f"{prompt_id}.md")
                assert len(prompt_text) > 0, f"{prompt_id}: prompt 内容为空"
            except Exception as e:
                errors.append(f"{prompt_id}: 加载失败 - {e}")
        
        if errors:
            pytest.fail("\n".join(errors))


class TestPromptStructure:
    """测试 prompt 结构校验。"""
    
    def test_prompt_structure(self):
        """测试所有 prompt 文件的结构校验。"""
        loader = PromptLoader()
        prompt_files = _get_all_prompt_files()
        
        assert len(prompt_files) > 0, "未找到任何 prompt 文件"
        
        all_errors = []
        for prompt_file in prompt_files:
            prompt_id = _get_prompt_id(prompt_file)
            try:
                # 使用 load_raw 获取完整内容（包含 frontmatter）
                prompt_text = loader.load_raw(f"{prompt_id}.md")
                errors = validate_prompt_text(prompt_id, prompt_text)
                if errors:
                    all_errors.extend(errors)
            except Exception as e:
                all_errors.append(f"{prompt_id}: 验证过程出错 - {e}")
        
        if all_errors:
            pytest.fail("\n".join(all_errors))


class TestPromptRendering:
    """测试 prompt 渲染功能。"""
    
    def test_prompt_rendering(self):
        """测试 prompt 渲染后不残留占位符。"""
        loader = PromptLoader()
        prompt_files = _get_all_prompt_files()
        
        assert len(prompt_files) > 0, "未找到任何 prompt 文件"
        
        errors = []
        for prompt_file in prompt_files:
            prompt_id = _get_prompt_id(prompt_file)
            try:
                prompt_text = loader.load(f"{prompt_id}.md")
                
                # 提取所有变量
                import re
                variables = set(re.findall(r"\{\{(\w+)\}\}", prompt_text))
                
                if not variables:
                    # 如果没有变量，跳过渲染测试
                    continue
                
                # 创建 dummy 变量值
                dummy_vars = {var: f"dummy_{var}_value" for var in variables}
                
                # 渲染（去掉 YAML frontmatter 后）
                if prompt_text.startswith("---"):
                    second_dash = prompt_text.find("\n---", 4)
                    if second_dash != -1:
                        prompt_text = prompt_text[second_dash + 5:].strip()
                
                rendered = loader.render(prompt_text, dummy_vars)
                
                # 检查是否还有未替换的占位符
                remaining = set(re.findall(r"\{\{(\w+)\}\}", rendered))
                if remaining:
                    errors.append(
                        f"{prompt_id}: 渲染后仍有未替换的变量: {', '.join(remaining)}"
                    )
            except Exception as e:
                errors.append(f"{prompt_id}: 渲染测试失败 - {e}")
        
        if errors:
            pytest.fail("\n".join(errors))


class TestSpecificPrompts:
    """针对特定 prompt 的详细测试。"""
    
    def test_router_llm_first_prompt(self):
        """测试 router/llm_first prompt。"""
        loader = PromptLoader()
        prompt_text = loader.load_raw("router/llm_first.md")
        
        # 验证结构
        errors = validate_prompt_text("router/llm_first", prompt_text)
        assert len(errors) == 0, f"router/llm_first 结构校验失败: {errors}"
        
        # 验证 parse 方法
        parsed = loader.parse("router/llm_first.md")
        assert "system" in parsed["sections"], "缺少 system 分段"
        assert "user" in parsed["sections"], "缺少 user 分段"
    
    def test_planner_default_prompt(self):
        """测试 planner/default prompt。"""
        loader = PromptLoader()
        prompt_text = loader.load_raw("planner/default.md")
        
        # 验证结构
        errors = validate_prompt_text("planner/default", prompt_text)
        assert len(errors) == 0, f"planner/default 结构校验失败: {errors}"
        
        # 验证 parse 方法
        parsed = loader.parse("planner/default.md")
        assert "system" in parsed["sections"], "缺少 system 分段"
    
    def test_qa_prompt(self):
        """测试 chat/qa prompt。"""
        loader = PromptLoader()
        prompt_text = loader.load_raw("chat/qa.md")
        
        # 验证结构
        errors = validate_prompt_text("chat/qa", prompt_text)
        assert len(errors) == 0, f"chat/qa 结构校验失败: {errors}"
        
        # 验证 parse 方法
        parsed = loader.parse("chat/qa.md")
        assert "system" in parsed["sections"], "缺少 system 分段"
