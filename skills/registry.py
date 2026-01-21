"""Skills registry."""
import warnings
from pathlib import Path
from typing import Dict, Optional, List, Any

from core.contracts.skill import JarvisSkill
from core.platform.config import Config
from skills.adapters.claude_code_adapter import ClaudeCodeAdapter
from skills.adapters.agentskills_adapter import AgentSkillsAdapter


class SkillsRegistry:
    """技能注册表。"""
    
    def __init__(self, workspace_dir: str = "./skills_workspace"):
        """初始化技能注册表。
        
        Args:
            workspace_dir: 技能工作空间目录
        """
        self.workspace_dir = Path(workspace_dir)
        self.skills: Dict[str, JarvisSkill] = {}
        self.adapters: List[Any] = []
        
        # 加载启用的适配器
        self._load_adapters()
    
    def _load_adapters(self) -> None:
        """根据配置加载启用的适配器。"""
        config = Config()
        skills_profile = config.load_yaml("skills_profile.yaml")
        
        # 获取启用的技能列表，如果不存在或为空则默认启用 claude_code
        enabled_skills = skills_profile.get("enabled_skills", [])
        if not enabled_skills:
            enabled_skills = ["claude_code"]
        
        # 加载每个启用的适配器
        for adapter_name in enabled_skills:
            try:
                if adapter_name == "claude_code":
                    self.adapters.append(ClaudeCodeAdapter())
                elif adapter_name == "agentskills":
                    # agentskills 是 stub，优雅跳过并给出 warn
                    adapter = AgentSkillsAdapter()
                    # 检查是否是 stub：检查 parse_skill_file 方法的文档字符串
                    # v0.1 中 agentskills 是 stub，总是返回 None
                    import inspect
                    doc = inspect.getdoc(adapter.parse_skill_file) or ""
                    # 如果文档中包含 "占位" 或 "stub"，认为是 stub
                    if "占位" in doc or "stub" in doc.lower() or "TODO" in doc:
                        warnings.warn(
                            f"Adapter 'agentskills' is a stub and not fully implemented. "
                            f"Skipping agent skills adapter loading.",
                            UserWarning
                        )
                        continue
                    self.adapters.append(adapter)
                else:
                    warnings.warn(
                        f"Unknown adapter name: {adapter_name}. Skipping.",
                        UserWarning
                    )
            except Exception as e:
                warnings.warn(
                    f"Failed to load adapter '{adapter_name}': {e}. Skipping.",
                    UserWarning
                )
        
        # 如果没有任何适配器被加载，默认加载 claude_code
        if not self.adapters:
            self.adapters.append(ClaudeCodeAdapter())
    
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
                # 尝试使用所有适配器解析技能文件
                jarvis_skill = None
                for adapter in self.adapters:
                    # 尝试使用 parse_skill_md 方法（claude_code）
                    if hasattr(adapter, "parse_skill_md"):
                        jarvis_skill = adapter.parse_skill_md(str(skill_md_path))
                        if jarvis_skill:
                            break
                    # 尝试使用 parse_skill_file 方法（agentskills）
                    elif hasattr(adapter, "parse_skill_file"):
                        jarvis_skill = adapter.parse_skill_file(str(skill_md_path))
                        if jarvis_skill:
                            break
                
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
