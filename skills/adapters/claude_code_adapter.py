"""Claude Code adapter."""
import re
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from core.contracts.skill import JarvisSkill


class ClaudeCodeAdapter:
    """Claude Code 技能适配器（解析 SKILL.md）。"""
    
    @staticmethod
    def parse_skill_md(file_path: str) -> Optional[JarvisSkill]:
        """解析 Claude Code 风格的 SKILL.md 文件。
        
        Args:
            file_path: SKILL.md 文件路径
            
        Returns:
            JarvisSkill 对象，如果解析失败则返回 None
        """
        path = Path(file_path)
        if not path.exists():
            return None
        
        try:
            content = path.read_text(encoding="utf-8")
            
            # 解析 YAML frontmatter
            frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
            match = re.match(frontmatter_pattern, content, re.DOTALL)
            
            if not match:
                # 如果没有 frontmatter，尝试解析整个文件作为 Markdown
                metadata = {}
                instructions_md = content
            else:
                yaml_content = match.group(1)
                instructions_md = match.group(2)
                
                # 解析 YAML
                metadata = yaml.safe_load(yaml_content) or {}
            
            # 提取必需字段
            skill_id = path.parent.name  # 使用目录名作为 skill_id
            name = metadata.get("name", skill_id)
            description = metadata.get("description", "")
            tags = metadata.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            
            # 移除 metadata 中已提取的字段
            remaining_metadata = {k: v for k, v in metadata.items() 
                                 if k not in ("name", "description", "tags")}
            
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
            print(f"解析 SKILL.md 失败 {file_path}: {e}")
            return None
