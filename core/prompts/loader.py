"""Prompt loader for centralized prompt management."""
import re
from pathlib import Path
from typing import Dict, Optional, Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class PromptLoader:
    """加载和管理 LLM prompts 的工具类。
    
    从 prompts/ 目录加载 prompt 文件，支持变量替换和结构化解析。
    """
    
    def __init__(self, project_root: Optional[str] = None):
        """初始化 PromptLoader。
        
        Args:
            project_root: 项目根目录路径。如果为 None，自动检测（从当前文件向上查找包含 prompts/ 的目录）。
        """
        if project_root:
            self.project_root = Path(project_root)
        else:
            # 自动检测项目根目录（从当前文件位置向上查找）
            current_file = Path(__file__).resolve()
            # 从 core/prompts/loader.py 向上找到项目根目录
            self.project_root = current_file.parent.parent.parent
        
        self.prompts_dir = self.project_root / "prompts"
        if not self.prompts_dir.exists():
            raise FileNotFoundError(
                f"prompts/ 目录不存在: {self.prompts_dir}"
            )
    
    def _get_prompt_path(self, prompt_id: str) -> Path:
        """获取 prompt 文件路径（带安全检查）。
        
        Args:
            prompt_id: prompt 文件路径，相对于 prompts/ 目录
        
        Returns:
            Path 对象
        
        Raises:
            ValueError: 如果路径不安全
            FileNotFoundError: 如果文件不存在
        """
        prompt_path = self.prompts_dir / prompt_id
        # 规范化路径，确保在 prompts_dir 内
        try:
            prompt_path = prompt_path.resolve()
            if not str(prompt_path).startswith(str(self.prompts_dir.resolve())):
                raise ValueError(f"prompt_id 路径不安全: {prompt_id}")
        except (OSError, ValueError) as e:
            raise ValueError(f"无效的 prompt_id: {prompt_id}") from e
        
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"Prompt 文件不存在: {prompt_path} (prompt_id: {prompt_id})"
            )
        
        return prompt_path
    
    def load_raw(self, prompt_id: str) -> str:
        """读取 prompt 文件原文（包含 YAML frontmatter）。
        
        Args:
            prompt_id: prompt 文件路径，相对于 prompts/ 目录。
                      例如 "router/llm_first.md" 会加载 prompts/router/llm_first.md
        
        Returns:
            prompt 文件完整内容（包含 frontmatter）
        
        Raises:
            FileNotFoundError: 如果文件不存在
        """
        prompt_path = self._get_prompt_path(prompt_id)
        return prompt_path.read_text(encoding="utf-8")
    
    def load(self, prompt_id: str) -> str:
        """加载 prompt 文件正文（去掉 YAML frontmatter）。
        
        Args:
            prompt_id: prompt 文件路径，相对于 prompts/ 目录。
                      例如 "router/llm_first.md" 会加载 prompts/router/llm_first.md
        
        Returns:
            prompt 文件正文（去掉 frontmatter）
        
        Raises:
            FileNotFoundError: 如果文件不存在
        """
        raw_text = self.load_raw(prompt_id)
        
        # 去掉 YAML frontmatter（以第一个 "---" 开始，第二个 "---" 结束）
        if raw_text.startswith("---"):
            second_dash = raw_text.find("\n---", 4)
            if second_dash != -1:
                return raw_text[second_dash + 5:].strip()
        
        return raw_text.strip()
    
    def parse(self, prompt_id: str) -> Dict[str, Any]:
        """解析 prompt 文件，返回结构化数据。
        
        Args:
            prompt_id: prompt 文件路径
        
        Returns:
            字典，包含：
            - "meta": frontmatter 字典
            - "sections": 分段字典，包含 "system", "user", "assistant"（如果存在）
        
        Raises:
            FileNotFoundError: 如果文件不存在
            ValueError: 如果缺少必需的 system 分段
        """
        raw_text = self.load_raw(prompt_id)
        
        # 解析 frontmatter
        meta = {}
        content = raw_text
        
        if raw_text.startswith("---"):
            second_dash = raw_text.find("\n---", 4)
            if second_dash != -1:
                frontmatter_text = raw_text[4:second_dash].strip()
                content = raw_text[second_dash + 5:].strip()
                
                # 解析 YAML
                if HAS_YAML:
                    try:
                        meta = yaml.safe_load(frontmatter_text) or {}
                        if not isinstance(meta, dict):
                            meta = {}
                    except Exception:
                        # YAML 解析失败，尝试最小解析
                        meta = self._parse_frontmatter_minimal(frontmatter_text)
                else:
                    meta = self._parse_frontmatter_minimal(frontmatter_text)
        
        # 解析分段
        sections = self._parse_sections(content)
        
        # 检查必需分段
        if "system" not in sections:
            raise ValueError(
                f"Prompt {prompt_id} 缺少必需的 '## system' 分段"
            )
        
        return {
            "meta": meta,
            "sections": sections,
        }
    
    def _parse_frontmatter_minimal(self, frontmatter_text: str) -> Dict[str, Any]:
        """最小化解析 YAML frontmatter（不依赖 yaml 库）。
        
        Args:
            frontmatter_text: frontmatter 文本
        
        Returns:
            解析后的字典
        """
        result = {}
        for line in frontmatter_text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line and not line.startswith("-"):
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                # 处理引号
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                result[key] = value
        return result
    
    def _parse_sections(self, content: str) -> Dict[str, str]:
        """解析 prompt 内容的分段。
        
        Args:
            content: prompt 正文内容
        
        Returns:
            分段字典，键为 "system", "user", "assistant"（如果存在）
        """
        sections = {}
        
        # 使用正则表达式匹配 ## system, ## user, ## assistant
        pattern = r"##\s+(system|user|assistant)\s*\n(.*?)(?=##\s+(?:system|user|assistant)|$)"
        matches = re.finditer(pattern, content, re.DOTALL)
        
        for match in matches:
            role = match.group(1).lower()
            section_content = match.group(2).strip()
            sections[role] = section_content
        
        return sections
    
    def render(self, prompt: str, vars: Dict[str, str], strict: bool = True) -> str:
        """渲染 prompt 模板，替换变量占位符。
        
        Args:
            prompt: prompt 模板字符串
            vars: 变量字典，键为变量名（不含 {{}}），值为替换值
            strict: 如果为 True，检测所有 {{var}}，若 vars 缺失则抛 ValueError
        
        Returns:
            渲染后的 prompt 字符串
        
        Raises:
            ValueError: 如果 strict=True 且存在未提供的变量
        
        示例:
            >>> loader = PromptLoader()
            >>> template = "你好，{{name}}！"
            >>> loader.render(template, {"name": "世界"})
            "你好，世界！"
            >>> loader.render(template, {}, strict=True)
            ValueError: 缺少变量: name
        """
        # 提取所有变量
        pattern = r"\{\{(\w+)\}\}"
        variables_in_text = set(re.findall(pattern, prompt))
        
        if strict:
            # 检查是否有缺失的变量
            missing = variables_in_text - set(vars.keys())
            if missing:
                raise ValueError(
                    f"缺少变量: {', '.join(sorted(missing))}。"
                    f"提供的变量: {', '.join(sorted(vars.keys()))}"
                )
        
        # 渲染变量
        result = prompt
        for key, value in vars.items():
            # 替换 {{key}} 格式的占位符
            pattern = r"\{\{" + re.escape(key) + r"\}\}"
            result = re.sub(pattern, str(value), result)
        
        # 如果 strict=False，将未提供的变量替换为空字符串
        if not strict:
            for var in variables_in_text:
                if var not in vars:
                    pattern = r"\{\{" + re.escape(var) + r"\}\}"
                    result = re.sub(pattern, "", result)
        
        return result
    
    def load_and_render(self, prompt_id: str, vars: Optional[Dict[str, str]] = None, strict: bool = True) -> str:
        """加载并渲染 prompt（便捷方法）。
        
        Args:
            prompt_id: prompt 文件路径
            vars: 可选的变量字典
            strict: 是否严格模式
        
        Returns:
            渲染后的 prompt 字符串
        """
        prompt = self.load(prompt_id)
        if vars:
            prompt = self.render(prompt, vars, strict=strict)
        return prompt
