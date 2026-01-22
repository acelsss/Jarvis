"""Agent Skills adapter."""
import re
from typing import Dict, Any, Optional
from pathlib import Path
import yaml

from core.contracts.skill import JarvisSkill


class AgentSkillsAdapter:
    """Agent Skills 标准适配器（符合 Anthropic Agent Skills 规范）。"""
    
    @staticmethod
    def parse_skill_file(file_path: str) -> Optional[JarvisSkill]:
        """解析 Agent Skills 标准格式的技能文件。
        
        根据 Anthropic Agent Skills 标准：
        - SKILL.md 必须以 YAML frontmatter 开头
        - frontmatter 必须包含 name 和 description
        - 支持可选的 license、compatibility、metadata 等字段
        - 支持引用其他文件（reference.md, forms.md 等）
        
        Args:
            file_path: SKILL.md 文件路径
            
        Returns:
            JarvisSkill 对象，如果解析失败则返回 None
        """
        path = Path(file_path)
        if not path.exists():
            return None
        
        # 检查文件名必须是 SKILL.md
        if path.name != "SKILL.md":
            return None
        
        try:
            content = path.read_text(encoding="utf-8")
            
            # 解析 YAML frontmatter
            frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
            match = re.match(frontmatter_pattern, content, re.DOTALL)
            
            if not match:
                # Agent Skills 标准要求必须有 frontmatter
                return None
            
            yaml_content = match.group(1)
            instructions_md = match.group(2)
            
            # 解析 YAML
            metadata = yaml.safe_load(yaml_content) or {}
            
            # Agent Skills 标准要求：name 和 description 是必需的
            if "name" not in metadata or "description" not in metadata:
                return None
            
            # 提取必需字段
            skill_id = path.parent.name  # 使用目录名作为 skill_id
            name = metadata.get("name", skill_id)
            description = metadata.get("description", "")
            
            # 验证 name 格式（根据标准：1-64字符，小写字母、数字、连字符）
            if not re.match(r'^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$', name.lower()):
                # 如果不符合标准格式，使用 skill_id
                name = skill_id
            
            tags = metadata.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            
            # 提取其他标准字段
            license_info = metadata.get("license", "")
            compatibility = metadata.get("compatibility", "")
            allowed_tools = metadata.get("allowed-tools", [])
            if isinstance(allowed_tools, str):
                allowed_tools = allowed_tools.split()
            
            # 移除 metadata 中已提取的字段
            remaining_metadata = {
                k: v for k, v in metadata.items() 
                if k not in ("name", "description", "tags", "license", "compatibility", "allowed-tools")
            }
            
            # 添加标准字段到 metadata
            if license_info:
                remaining_metadata["license"] = license_info
            if compatibility:
                remaining_metadata["compatibility"] = compatibility
            if allowed_tools:
                remaining_metadata["allowed-tools"] = allowed_tools
            
            return JarvisSkill(
                skill_id=skill_id,
                name=name,
                description=description,
                tags=tags,
                instructions_md=instructions_md.strip(),
                metadata=remaining_metadata,
                file_path=str(path),
            )
        except Exception as e:
            print(f"解析 Agent Skills 格式失败 {file_path}: {e}")
            return None
