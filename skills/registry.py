"""Skills registry."""
from pathlib import Path
from typing import Dict, Optional, List

from core.contracts.skill import JarvisSkill
from skills.adapters.claude_code_adapter import ClaudeCodeAdapter


class SkillsRegistry:
    """技能注册表。"""
    
    def __init__(self, workspace_dir: str = "./skills_workspace"):
        """初始化技能注册表。
        
        Args:
            workspace_dir: 技能工作空间目录
        """
        self.workspace_dir = Path(workspace_dir)
        self.skills: Dict[str, JarvisSkill] = {}
        self.adapter = ClaudeCodeAdapter()
    
    def scan_workspace(self) -> None:
        """扫描工作空间目录，加载所有技能。"""
        if not self.workspace_dir.exists():
            print(f"警告: 技能工作空间目录不存在: {self.workspace_dir}")
            return
        
        # 扫描所有包含 SKILL.md 的子目录
        for skill_dir in self.workspace_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            skill_md_path = skill_dir / "SKILL.md"
            if skill_md_path.exists():
                jarvis_skill = self.adapter.parse_skill_md(str(skill_md_path))
                if jarvis_skill:
                    self.skills[jarvis_skill.skill_id] = jarvis_skill
                    print(f"已加载技能: {jarvis_skill.name} ({jarvis_skill.skill_id})")
    
    def register(self, skill: JarvisSkill) -> None:
        """注册技能。"""
        self.skills[skill.skill_id] = skill
    
    def get(self, skill_id: str) -> Optional[JarvisSkill]:
        """获取技能。"""
        return self.skills.get(skill_id)
    
    def list_all(self) -> Dict[str, JarvisSkill]:
        """列出所有技能。"""
        return self.skills.copy()
    
    def search_by_tags(self, tags: List[str]) -> List[JarvisSkill]:
        """根据标签搜索技能。
        
        Args:
            tags: 标签列表
            
        Returns:
            匹配的技能列表
        """
        results = []
        for skill in self.skills.values():
            if any(tag in skill.tags for tag in tags):
                results.append(skill)
        return results
    
    def search_by_keyword(self, keyword: str) -> List[JarvisSkill]:
        """根据关键词搜索技能（搜索名称、描述、标签）。
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的技能列表
        """
        keyword_lower = keyword.lower()
        results = []
        for skill in self.skills.values():
            if (keyword_lower in skill.name.lower() or
                keyword_lower in skill.description.lower() or
                any(keyword_lower in tag.lower() for tag in skill.tags)):
                results.append(skill)
        return results
