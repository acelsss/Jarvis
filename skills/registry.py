"""Skills registry."""
import warnings
from pathlib import Path
from typing import Dict, Optional, List, Any
import yaml

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
    
    def scan_workspace(self, load_fulltext: bool = False) -> None:
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
                if load_fulltext:
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
                else:
                    metadata = self._load_frontmatter(skill_md_path)
                    tags = metadata.get("tags", [])
                    if isinstance(tags, str):
                        tags = [tags]
                    jarvis_skill = JarvisSkill(
                        skill_id=skill_dir.name,
                        name=metadata.get("name") or skill_dir.name,
                        description=metadata.get("description") or "",
                        tags=tags,
                        instructions_md="",
                        metadata={
                            k: v
                            for k, v in metadata.items()
                            if k not in ("name", "description", "tags")
                        },
                        file_path=str(skill_md_path),
                    )
                
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

    def _load_frontmatter(self, skill_md_path: Path) -> Dict[str, Any]:
        """仅读取 YAML frontmatter，避免读取全文。"""
        try:
            with skill_md_path.open("r", encoding="utf-8") as handle:
                first_line = handle.readline()
                if not first_line.strip().startswith("---"):
                    return {}

                yaml_lines: List[str] = []
                for line in handle:
                    if line.strip() == "---":
                        break
                    yaml_lines.append(line)

            if not yaml_lines:
                return {}
            return yaml.safe_load("".join(yaml_lines)) or {}
        except Exception as exc:
            print(f"读取 frontmatter 失败 {skill_md_path}: {exc}")
            return {}

    def _normalize_skill_metadata(
        self,
        skill_id: str,
        metadata: Dict[str, Any],
        skill_dir: Path,
    ) -> Dict[str, Any]:
        name = metadata.get("name") or skill_id
        description = metadata.get("description") or ""
        tags = metadata.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        allowed_tools = (
            metadata.get("allowed_tools")
            or metadata.get("allowed-tools")
            or []
        )
        if isinstance(allowed_tools, str):
            allowed_tools = [allowed_tools]

        disable_model_invocation = (
            metadata.get("disable_model_invocation")
            if "disable_model_invocation" in metadata
            else metadata.get("disable-model-invocation", False)
        )

        return {
            "id": skill_id,
            "name": name,
            "description": description,
            "tags": tags,
            "allowed_tools": allowed_tools,
            "disable_model_invocation": bool(disable_model_invocation),
            "path": skill_dir.as_posix(),
        }

    def _metadata_from_skill(self, skill: JarvisSkill) -> Dict[str, Any]:
        return self._normalize_skill_metadata(
            skill.skill_id,
            {
                "name": skill.name,
                "description": skill.description,
                "tags": skill.tags,
                **(skill.metadata or {}),
            },
            Path(skill.file_path).parent if skill.file_path else self.workspace_dir / skill.skill_id,
        )

    def list_skill_metadata(self) -> List[Dict[str, Any]]:
        """列出技能元信息（只读 frontmatter，不读全文）。"""
        if self.skills:
            return [self._metadata_from_skill(skill) for skill in self.skills.values()]

        results: List[Dict[str, Any]] = []
        if not self.workspace_dir.exists():
            return results

        for skill_dir in self.workspace_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_id = skill_dir.name
            skill_md_path = skill_dir / "SKILL.md"
            if skill_md_path.exists():
                metadata = self._load_frontmatter(skill_md_path)
                results.append(self._normalize_skill_metadata(skill_id, metadata, skill_dir))
                continue

            # 非 SKILL.md 结构：尝试从已注册技能中提取，缺失则默认
            existing = self.skills.get(skill_id)
            if existing:
                results.append(self._metadata_from_skill(existing))
            else:
                results.append(
                    self._normalize_skill_metadata(skill_id, {}, skill_dir)
                )

        return results

    def load_skill_fulltext(self, skill_id: str) -> str:
        """加载指定技能的完整说明文本。"""
        # 优先读取 SKILL.md 全文
        skill_dir = self.workspace_dir / skill_id
        skill_md_path = skill_dir / "SKILL.md"
        if skill_md_path.exists():
            return skill_md_path.read_text(encoding="utf-8")

        skill = self.skills.get(skill_id)
        if skill:
            if skill.instructions_md:
                return skill.instructions_md
            if skill.file_path:
                path = Path(skill.file_path)
                if path.exists():
                    return path.read_text(encoding="utf-8")

        return ""
    
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
