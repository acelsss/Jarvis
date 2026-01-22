"""Python script execution tool (sandboxed, allowlisted, audited)."""
import os
import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, Any, Optional

from core.contracts.tool import Tool
from core.contracts.risk import RISK_LEVEL_R2
from core.platform.config import Config


class PythonRunTool(Tool):
    """Python 脚本执行工具（沙箱化、白名单、审计）。
    
    只允许执行以下路径的脚本：
    1. skills_workspace/**/scripts/*.py
    2. sandbox/scripts/*.py
    
    安全措施：
    - realpath 校验，防止路径逃逸
    - 禁止 symlink 逃逸
    - 不经 shell，直接使用 subprocess.run
    - cwd 强制为 sandbox 根目录
    - 超时控制（默认 60 秒，上限 120 秒）
    - stdout/stderr 截断（各最多 2048 字符）
    - env 白名单（允许 JARVIS_ 开头）
    """
    
    # 输出截断长度
    MAX_OUTPUT_LENGTH = 2048
    
    # 超时上限（秒）
    MAX_TIMEOUT = 120
    
    # 默认超时（秒）
    DEFAULT_TIMEOUT = 60
    
    # 产物差分：最多返回的文件数
    MAX_ARTIFACTS = 200
    
    # 审计日志：最多展示的产物样本数
    MAX_ARTIFACTS_SAMPLE = 20
    
    def __init__(self, project_root: str = None, sandbox_root: str = None):
        """初始化 Python 执行工具。
        
        Args:
            project_root: 项目根目录（如果为None则自动检测）
            sandbox_root: 沙箱根目录（如果为None则从配置读取）
        """
        # 检测项目根目录
        if project_root is None:
            # 从当前文件位置向上查找，找到包含 .git 或 pyproject.toml 的目录
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent
            # 如果存在 .git 或 pyproject.toml，说明这是项目根目录
            if not (project_root / ".git").exists() and not (project_root / "pyproject.toml").exists():
                # 尝试再向上一级
                project_root = project_root.parent
        
        self.project_root = Path(project_root).resolve()
        
        # 获取沙箱目录
        if sandbox_root is None:
            config = Config()
            preferences = config.load_yaml("preferences.yaml")
            sandbox_root = preferences.get("sandbox", {}).get("sandbox_root", "./sandbox")
            sandbox_root = os.getenv("SANDBOX_ROOT", sandbox_root)
        
        self.sandbox_root = Path(sandbox_root).resolve()
        # 确保沙箱目录存在
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        
        # 允许的脚本根目录
        self.allowed_roots = [
            self.project_root / "skills_workspace",
            self.project_root / "sandbox",
        ]
        
        super().__init__(
            tool_id="python_run",
            name="Python Script Runner",
            description=(
                "执行 Python 脚本（仅允许 skills_workspace/**/scripts/*.py 和 sandbox/scripts/*.py）。"
                "使用 realpath 校验防止路径逃逸，cwd 强制为 sandbox 根目录，"
                "默认超时 60 秒（上限 120 秒），风险等级 R2（需要审批）。"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "script_path": {
                        "type": "string",
                        "description": "脚本路径（相对于项目根目录）",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "脚本参数列表",
                        "default": [],
                    },
                    "timeout_seconds": {
                        "type": "integer",
                        "description": "超时时间（秒，默认 60，上限 120）",
                        "default": 60,
                        "minimum": 1,
                        "maximum": 120,
                    },
                    "env": {
                        "type": "object",
                        "additionalProperties": {"type": "string"},
                        "description": "环境变量（仅允许 JARVIS_ 开头的 key）",
                        "default": None,
                    },
                },
                "required": ["script_path"],
            },
            risk_level=RISK_LEVEL_R2,
            requires_approval=True,
        )
    
    def _validate_script_path(self, script_path: str) -> Path:
        """验证脚本路径是否允许执行。
        
        Args:
            script_path: 脚本路径（相对或绝对）
            
        Returns:
            解析后的绝对路径
            
        Raises:
            ValueError: 如果路径不允许执行
        """
        # 转换为 Path 对象
        if Path(script_path).is_absolute():
            script_abs = Path(script_path)
        else:
            # 相对路径，相对于项目根目录
            script_abs = (self.project_root / script_path).resolve()
        
        # 使用 realpath 解析，防止 symlink 逃逸
        script_real = script_abs.resolve()
        
        # 检查文件是否存在
        if not script_real.exists():
            raise FileNotFoundError(f"脚本文件不存在: {script_path}")
        
        # 检查必须是 .py 文件
        if not script_real.suffix == ".py":
            raise ValueError(f"脚本必须是 .py 文件: {script_path}")
        
        # 检查路径是否在允许的根目录下
        is_allowed = False
        for allowed_root in self.allowed_roots:
            try:
                relative = script_real.relative_to(allowed_root.resolve())
                # 检查路径格式
                parts = relative.parts
                
                # 对于 skills_workspace，必须包含 scripts/ 目录
                if allowed_root.name == "skills_workspace":
                    # 检查路径中是否包含 scripts/ 目录
                    if "scripts" in parts:
                        is_allowed = True
                        break
                # 对于 sandbox，必须在 scripts/ 目录下
                elif allowed_root.name == "sandbox":
                    if len(parts) >= 1 and parts[0] == "scripts":
                        is_allowed = True
                        break
            except ValueError:
                # 不在这个根目录下，继续检查下一个
                continue
        
        if not is_allowed:
            raise ValueError(
                f"脚本路径不允许执行: {script_path}\n"
                f"只允许以下路径：\n"
                f"  - skills_workspace/**/scripts/*.py\n"
                f"  - sandbox/scripts/*.py"
            )
        
        return script_real
    
    def _validate_env(self, env: Optional[Dict[str, str]]) -> Optional[Dict[str, str]]:
        """验证环境变量白名单。
        
        Args:
            env: 环境变量字典
            
        Returns:
            过滤后的环境变量字典（只包含允许的 key）
            
        Raises:
            ValueError: 如果包含不允许的 key
        """
        if env is None:
            return None
        
        allowed_env = {}
        for key, value in env.items():
            # 只允许 JARVIS_ 开头的 key
            if key.startswith("JARVIS_"):
                allowed_env[key] = value
            else:
                raise ValueError(
                    f"环境变量 key '{key}' 不在白名单中。"
                    f"只允许 JARVIS_ 开头的 key。"
                )
        
        return allowed_env if allowed_env else None
    
    def _truncate_output(self, text: str, max_length: int = None) -> str:
        """截断输出文本。
        
        Args:
            text: 原始文本
            max_length: 最大长度（默认使用 MAX_OUTPUT_LENGTH）
            
        Returns:
            截断后的文本
        """
        if max_length is None:
            max_length = self.MAX_OUTPUT_LENGTH
        
        if len(text) <= max_length:
            return text
        
        return text[:max_length] + f"\n... (截断，原始长度: {len(text)} 字符)"
    
    def _snapshot_sandbox(self) -> Dict[str, tuple]:
        """扫描 sandbox 目录，生成文件快照。
        
        Returns:
            字典 {rel_path: (mtime_ns, size)}
        """
        snapshot = {}
        
        if not self.sandbox_root.exists():
            return snapshot
        
        # 排除的目录和文件
        excluded_names = {"memory", ".gitkeep", ".git"}
        
        try:
            # 递归扫描 sandbox 目录
            for file_path in self.sandbox_root.rglob("*"):
                # 跳过排除的目录
                if any(excluded in file_path.parts for excluded in excluded_names):
                    continue
                
                # 只处理文件，跳过目录
                if not file_path.is_file():
                    continue
                
                try:
                    # 计算相对路径
                    rel_path = file_path.relative_to(self.sandbox_root)
                    rel_path_str = str(rel_path)
                    
                    # 获取文件统计信息
                    stat = file_path.stat()
                    snapshot[rel_path_str] = (stat.st_mtime_ns, stat.st_size)
                except (OSError, ValueError):
                    # 忽略无法访问的文件
                    continue
        except Exception:
            # 扫描失败时返回空快照
            pass
        
        return snapshot
    
    def _diff_snapshots(
        self, before: Dict[str, tuple], after: Dict[str, tuple]
    ) -> Dict[str, Any]:
        """计算两个快照之间的差分。
        
        Args:
            before: 执行前的快照 {rel_path: (mtime_ns, size)}
            after: 执行后的快照 {rel_path: (mtime_ns, size)}
            
        Returns:
            差分结果字典
        """
        artifacts_changed = []
        
        # 找出新增和变更的文件
        for rel_path, (mtime_ns, size) in after.items():
            if rel_path not in before:
                # 新增文件
                artifacts_changed.append({
                    "path": rel_path,
                    "size": size,
                    "kind": "added",
                })
            else:
                # 检查是否变更
                before_mtime, before_size = before[rel_path]
                if mtime_ns != before_mtime or size != before_size:
                    artifacts_changed.append({
                        "path": rel_path,
                        "size": size,
                        "kind": "modified",
                    })
        
        # 截断到最大数量
        truncated = len(artifacts_changed) > self.MAX_ARTIFACTS
        if truncated:
            artifacts_changed = artifacts_changed[:self.MAX_ARTIFACTS]
        
        return {
            "artifacts_changed": artifacts_changed,
            "artifacts_count": len(artifacts_changed),
            "truncated": truncated,
        }
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Python 脚本。
        
        Args:
            params: 执行参数
                - script_path: 脚本路径（必需）
                - args: 脚本参数列表（可选，默认 []）
                - timeout_seconds: 超时时间（可选，默认 60，上限 120）
                - env: 环境变量（可选，仅允许 JARVIS_ 开头）
                
        Returns:
            执行结果字典
        """
        script_path = params.get("script_path")
        if not script_path:
            raise ValueError("script_path 参数是必需的")
        
        args = params.get("args", [])
        timeout_seconds = min(
            params.get("timeout_seconds", self.DEFAULT_TIMEOUT),
            self.MAX_TIMEOUT
        )
        env = params.get("env")
        
        # 验证脚本路径
        script_real = self._validate_script_path(script_path)
        
        # 验证环境变量
        allowed_env = self._validate_env(env)
        
        # 构建执行环境
        exec_env = os.environ.copy()
        if allowed_env:
            exec_env.update(allowed_env)
        
        # 执行前快照
        before_snapshot = self._snapshot_sandbox()
        
        # 记录开始时间
        start_time = time.time()
        
        try:
            # 执行脚本（不经 shell，直接使用 subprocess.run）
            result = subprocess.run(
                [sys.executable, str(script_real)] + args,
                cwd=str(self.sandbox_root),  # cwd 强制为 sandbox 根目录
                env=exec_env,
                timeout=timeout_seconds,
                capture_output=True,
                text=True,
            )
            
            # 计算执行时间
            duration_ms = int((time.time() - start_time) * 1000)
            
            # 执行后快照
            after_snapshot = self._snapshot_sandbox()
            
            # 计算差分
            diff_result = self._diff_snapshots(before_snapshot, after_snapshot)
            
            # 截断输出
            stdout_excerpt = self._truncate_output(result.stdout)
            stderr_excerpt = self._truncate_output(result.stderr)
            
            # 计算相对路径（用于返回）
            try:
                script_relative = script_real.relative_to(self.project_root)
            except ValueError:
                script_relative = script_real
            
            return {
                "ok": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout_excerpt": stdout_excerpt,
                "stderr_excerpt": stderr_excerpt,
                "artifacts_changed": diff_result["artifacts_changed"],
                "meta": {
                    "duration_ms": duration_ms,
                    "script_path": str(script_relative),
                    "args": args,
                    "cwd": str(self.sandbox_root),
                    "timeout_seconds": timeout_seconds,
                    "artifacts_count": diff_result["artifacts_count"],
                    "artifacts_truncated": diff_result["truncated"],
                },
            }
            
        except subprocess.TimeoutExpired:
            duration_ms = int((time.time() - start_time) * 1000)
            # 即使超时，也计算差分（可能部分执行产生了文件）
            after_snapshot = self._snapshot_sandbox()
            diff_result = self._diff_snapshots(before_snapshot, after_snapshot)
            raise TimeoutError(
                f"脚本执行超时（{timeout_seconds} 秒）: {script_path}"
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            # 即使失败，也计算差分（可能部分执行产生了文件）
            after_snapshot = self._snapshot_sandbox()
            diff_result = self._diff_snapshots(before_snapshot, after_snapshot)
            raise RuntimeError(f"脚本执行失败: {str(e)}")
