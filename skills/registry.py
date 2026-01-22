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
                    # Agent Skills 标准适配器（已实现完整支持）
                    adapter = AgentSkillsAdapter()
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
    
    def _discover_skill_files(self, skill_dir: Path) -> Dict[str, Path]:
        """发现技能目录中的支持文件。
        
        Args:
            skill_dir: 技能目录路径
            
        Returns:
            文件类型到路径的映射（如 {'scripts': [...], 'references': [...]}）
        """
        discovered = {
            'scripts': [],
            'references': [],
            'assets': [],
            'other_md': [],
        }
        
        if not skill_dir.exists():
            return discovered
        
        # 扫描常见子目录
        for subdir_name in ['scripts', 'references', 'assets']:
            subdir = skill_dir / subdir_name
            if subdir.exists() and subdir.is_dir():
                for file_path in subdir.rglob('*'):
                    if file_path.is_file():
                        discovered[subdir_name].append(file_path)
        
        # 扫描技能目录根目录下的其他Markdown文件（除了SKILL.md）
        for file_path in skill_dir.iterdir():
            if file_path.is_file() and file_path.suffix == '.md' and file_path.name != 'SKILL.md':
                discovered['other_md'].append(file_path)
        
        return discovered

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
                        # 优先尝试 parse_skill_file 方法（Agent Skills 标准）
                        if hasattr(adapter, "parse_skill_file"):
                            jarvis_skill = adapter.parse_skill_file(str(skill_md_path))
                            if jarvis_skill:
                                break
                        # 回退到 parse_skill_md 方法（Claude Code 风格）
                        elif hasattr(adapter, "parse_skill_md"):
                            jarvis_skill = adapter.parse_skill_md(str(skill_md_path))
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
                    # 发现技能目录中的支持文件
                    discovered_files = self._discover_skill_files(skill_dir)
                    if discovered_files:
                        # 将发现的文件信息添加到metadata中
                        jarvis_skill.metadata['discovered_files'] = {
                            'scripts': [str(f) for f in discovered_files['scripts']],
                            'references': [str(f) for f in discovered_files['references']],
                            'assets': [str(f) for f in discovered_files['assets']],
                            'other_md': [str(f) for f in discovered_files['other_md']],
                        }
                    
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

    def _scan_skill_scripts(self, skill_dir: Path) -> List[Dict[str, str]]:
        """扫描技能目录下的 scripts/*.py 文件。
        
        Args:
            skill_dir: 技能目录路径
            
        Returns:
            脚本列表，每个元素包含 name 和 relative_path
        """
        scripts = []
        scripts_dir = skill_dir / "scripts"
        
        if not scripts_dir.exists() or not scripts_dir.is_dir():
            return scripts
        
        # 只扫描 scripts/ 目录下的 .py 文件（不递归）
        for file_path in scripts_dir.iterdir():
            if file_path.is_file() and file_path.suffix == ".py":
                # 计算相对路径（相对于技能目录）
                try:
                    relative_path = file_path.relative_to(skill_dir)
                    scripts.append({
                        "name": file_path.name,
                        "relative_path": str(relative_path),
                    })
                except ValueError:
                    # 如果无法计算相对路径，跳过
                    continue
        
        return scripts

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

        # 扫描 scripts 目录
        scripts = self._scan_skill_scripts(skill_dir)

        return {
            "id": skill_id,
            "name": name,
            "description": description,
            "tags": tags,
            "allowed_tools": allowed_tools,
            "disable_model_invocation": bool(disable_model_invocation),
            "path": skill_dir.as_posix(),
            "scripts": scripts,
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

    def _parse_file_references(self, content: str, skill_dir: Path) -> List[str]:
        """解析内容中引用的Markdown文件。
        
        Args:
            content: SKILL.md的内容
            skill_dir: 技能目录路径
            
        Returns:
            引用的文件路径列表（绝对路径字符串）
        """
        import re
        referenced_files = []
        seen_paths = set()
        
        # 匹配常见的文件引用模式：
        # - "see reference.md"
        # - "read forms.md"
        # - "see reference.md and forms.md"
        # - "For details, see reference.md"
        # - "参考 reference.md"
        # - "see reference.md, forms.md"
        patterns = [
            r'(?:see|read|参考|查看|see also|refer to|check|follow)\s+([a-zA-Z0-9_\-/]+\.md)',
            r'([a-zA-Z0-9_\-/]+\.md)(?:\s+and\s+([a-zA-Z0-9_\-/]+\.md))?',
            r'follow\s+the\s+instructions\s+in\s+([a-zA-Z0-9_\-/]+\.md)',
            r'([a-zA-Z0-9_\-/]+\.md)(?:\s*,\s*([a-zA-Z0-9_\-/]+\.md))?',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                for group in match.groups():
                    if group and group.endswith('.md'):
                        # 处理相对路径
                        if '/' in group:
                            file_path = skill_dir / group
                        else:
                            file_path = skill_dir / group
                        
                        # 标准化路径并检查是否存在
                        file_path = file_path.resolve()
                        if file_path.exists() and str(file_path) not in seen_paths:
                            referenced_files.append(str(file_path))
                            seen_paths.add(str(file_path))
        
        # 也检查技能目录中常见的文件（如果内容中提到了）
        common_files = ['reference.md', 'references.md', 'forms.md', 'guide.md', 'tutorial.md', 'README.md']
        for filename in common_files:
            file_path = skill_dir / filename
            if file_path.exists():
                file_path = file_path.resolve()
                # 检查内容中是否提到了这个文件（文件名或去掉扩展名）
                filename_base = filename.replace('.md', '')
                if (filename.lower() in content.lower() or 
                    filename_base.lower() in content.lower()):
                    if str(file_path) not in seen_paths:
                        referenced_files.append(str(file_path))
                        seen_paths.add(str(file_path))
        
        return referenced_files

    def load_skill_fulltext(self, skill_id: str, include_references: bool = False) -> str:
        """加载指定技能的完整说明文本。
        
        根据 Anthropic Agent Skills 的渐进式加载原则：
        - 默认只加载 SKILL.md 主文件（第二层）
        - SKILL.md 中已经包含了引用文件的提示（如 "see reference.md"）
        - LLM 可以根据 SKILL.md 中的提示，在需要时通过文件工具读取引用文件
        - 这符合渐进式加载的第三层：按需加载
        
        Args:
            skill_id: 技能ID
            include_references: 是否自动加载引用的文件内容（默认False，符合渐进式加载原则）
                              - False: 只返回 SKILL.md（推荐，符合标准）
                              - True: 返回 SKILL.md + 所有引用文件内容（向后兼容）
            
        Returns:
            技能说明文本
        """
        # 优先读取 SKILL.md 全文
        skill_dir = self.workspace_dir / skill_id
        skill_md_path = skill_dir / "SKILL.md"
        
        main_content = ""
        if skill_md_path.exists():
            main_content = skill_md_path.read_text(encoding="utf-8")
        else:
            skill = self.skills.get(skill_id)
            if skill:
                if skill.instructions_md:
                    main_content = skill.instructions_md
                elif skill.file_path:
                    path = Path(skill.file_path)
                    if path.exists():
                        main_content = path.read_text(encoding="utf-8")
        
        if not main_content:
            return ""
        
        # 根据渐进式加载原则：默认不自动加载引用文件
        # SKILL.md 中已经包含了引用提示（如 "see reference.md"）
        # LLM 可以根据需要决定是否读取这些文件
        if not include_references:
            return main_content
        
        # 向后兼容：如果明确要求加载引用文件，则加载
        # 解析并加载引用的文件
        referenced_files = self._parse_file_references(main_content, skill_dir)
        
        if not referenced_files:
            return main_content
        
        # 构建完整内容：主文件 + 引用的文件
        full_content = [main_content]
        full_content.append("\n\n---\n\n## 引用的参考文件\n\n")
        
        for ref_file_path in referenced_files:
            try:
                ref_path = Path(ref_file_path)
                if ref_path.exists():
                    ref_content = ref_path.read_text(encoding="utf-8")
                    # 提取文件名（不含路径）
                    filename = ref_path.name
                    full_content.append(f"### {filename}\n\n")
                    full_content.append(ref_content)
                    full_content.append("\n\n---\n\n")
            except Exception as e:
                # 如果加载引用文件失败，记录警告但继续
                print(f"警告: 无法加载引用文件 {ref_file_path}: {e}")
        
        return "".join(full_content)
    
    def list_skill_references(self, skill_id: str) -> List[Dict[str, str]]:
        """列出技能的引用文件信息（不加载内容）。
        
        Args:
            skill_id: 技能ID
            
        Returns:
            引用文件列表，每个元素包含 'name' 和 'path'
        """
        skill_dir = self.workspace_dir / skill_id
        skill_md_path = skill_dir / "SKILL.md"
        
        if not skill_md_path.exists():
            return []
        
        main_content = skill_md_path.read_text(encoding="utf-8")
        referenced_files = self._parse_file_references(main_content, skill_dir)
        
        references = []
        for ref_file_path in referenced_files:
            try:
                ref_path = Path(ref_file_path)
                if ref_path.exists():
                    references.append({
                        'name': ref_path.name,
                        'path': str(ref_path.relative_to(skill_dir)),
                        'full_path': str(ref_path),
                    })
            except Exception:
                pass
        
        return references
    
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
