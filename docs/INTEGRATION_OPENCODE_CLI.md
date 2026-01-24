# OpenCode CLI 集成方案（A 线路）

## 背景与目标

Jarvis 作为总控系统，需要按需调用外部编码 Agent 执行代码修改任务。本方案规划通过 CLI 方式集成 [OpenCode](https://github.com/anomalyco/opencode)（anomalyco/opencode），使 Jarvis 能够：

- 在受控的 workspace 环境中调用 OpenCode 执行编码任务
- 通过统一的 Tool 接口接入，确保风险门控、审计与产物差分
- 与 Skills 系统结合，提供可复用的编码工作流

**设计原则**：
- 所有执行必须通过 Tool Runner，受风险门控约束
- 默认禁止直接操作真实工程目录，强制使用 sandbox/workspaces
- 完整的审计日志与产物差分追踪

---

## 什么是 CLI 调用

CLI 调用指 Jarvis 使用 Python `subprocess` 模块，在指定的 workspace/repo 目录下执行 `opencode` 命令。

**执行方式**：
- 使用 `subprocess.run()` 或 `subprocess.Popen()`（异步场景）
- 工作目录（`cwd`）限制在 `sandbox/workspaces/` 下的子目录
- 不通过 shell 执行（`shell=False`），直接传递命令与参数列表
- 捕获 stdout/stderr，设置超时保护

**示例调用**：
```python
subprocess.run(
    ["opencode", "--task", "修复这个函数的类型注解", "--file", "src/main.py"],
    cwd="sandbox/workspaces/test_repo",
    capture_output=True,
    text=True,
    timeout=300
)
```

---

## 前置条件

### 系统要求

1. **OpenCode 安装**：
   - 系统必须已安装 OpenCode CLI，能在终端执行 `opencode --help`
   - 建议通过包管理器（如 pip、npm、brew）安装，确保在 PATH 中可用
   - 版本兼容性：待确认（见“已知不确定性与待确认事项”）

2. **Workspace 准备**：
   - 默认策略：**禁止直接操作真实工程目录**
   - 必须在 `sandbox/workspaces/` 下复制或准备待修改的 repo
   - 建议提供工具函数：`prepare_workspace(source_repo_path, workspace_name)`
   - Workspace 命名规范：`{repo_name}_{timestamp}` 或 `{repo_name}_{task_id}`

3. **权限与隔离**：
   - Workspace 目录应具备读写权限
   - 建议使用独立的工作目录，避免污染原始 repo
   - 如需 git 操作，应在 workspace 内初始化或复制 `.git`（可选）

---

## 集成方式（Tool 设计）

### Tool 定义

**Tool ID**: `opencode_run`

**风险等级**: 默认 `R3`（会修改代码、执行命令），至少 `R2` + 强审批

**描述**: 在指定 workspace 目录下通过 CLI 调用 OpenCode 执行编码任务

### 输入参数 Schema（建议）

```json
{
  "type": "object",
  "required": ["workspace_path", "task_prompt"],
  "properties": {
    "workspace_path": {
      "type": "string",
      "description": "工作目录路径，必须位于 sandbox/workspaces/ 下（相对路径或绝对路径，需校验）"
    },
    "task_prompt": {
      "type": "string",
      "description": "自然语言任务描述，传递给 OpenCode"
    },
    "timeout_seconds": {
      "type": "integer",
      "default": 300,
      "minimum": 10,
      "maximum": 3600,
      "description": "执行超时时间（秒），默认 300，上限可配置"
    },
    "output_mode": {
      "type": "string",
      "enum": ["diff", "inplace", "report"],
      "default": "diff",
      "description": "输出模式：diff（仅输出变更）、inplace（直接修改文件）、report（生成报告）"
    },
    "additional_args": {
      "type": "array",
      "items": {"type": "string"},
      "default": [],
      "description": "额外的 OpenCode CLI 参数（如 --model, --dry-run 等）"
    }
  }
}
```

### 执行流程

1. **参数校验**：
   - 验证 `workspace_path` 位于 `sandbox/workspaces/` 下（防止路径逃逸）
   - 验证 workspace 目录存在
   - 验证 `opencode` 命令可用（`subprocess.run(["opencode", "--version"], capture_output=True)`）

2. **执行前快照**：
   - 记录 workspace 目录的 git 状态（如有）或文件树快照
   - 用于后续产物差分

3. **构建命令**：
   ```python
   cmd = ["opencode"]
   if output_mode == "diff":
       cmd.extend(["--output", "diff"])
   elif output_mode == "inplace":
       cmd.extend(["--output", "inplace"])
   cmd.extend(["--task", task_prompt])
   cmd.extend(additional_args)
   ```

4. **执行调用**：
   ```python
   result = subprocess.run(
       cmd,
       cwd=workspace_path,
       capture_output=True,
       text=True,
       timeout=timeout_seconds
   )
   ```

5. **执行后差分**：
   - 对比执行前后的文件变更（git diff 或文件系统对比）
   - 生成 `changed_files` 列表

6. **输出截断**：
   - stdout/stderr 截断到合理长度（建议 2048 字符），避免日志爆炸
   - 完整输出可写入临时文件，路径记录在 `evidence_refs` 中

### 返回值结构

```python
{
    "success": bool,
    "exit_code": int,
    "stdout_excerpt": str,  # 截断后的输出
    "stderr_excerpt": str,  # 截断后的错误输出
    "changed_files": List[str],  # 变更文件列表（相对路径）
    "diff_summary": str,  # 变更摘要（可选）
    "duration_ms": int,
    "evidence_refs": [
        "sandbox/workspaces/xxx_repo/.opencode_output.log",  # 完整日志路径
        "sandbox/workspaces/xxx_repo/.opencode_diff.patch"   # diff 文件路径（如适用）
    ]
}
```

---

## 风险与审批策略

### 风险等级

**默认风险等级：R3**

理由：
- 会修改代码文件（可能不可逆）
- 执行外部命令（opencode），存在执行环境风险
- 可能影响项目构建、测试、依赖等

**最低要求：R2 + 强审批**

即使降级到 R2，也必须：
- 强制审批（`requires_approval=True`）
- 审批时展示：workspace 路径、任务提示、预期影响范围
- 审批后记录审批决策到审计日志

### 为何不能直接用通用 shell 工具

**边界与审计需求**：

1. **专用工具需要专门的审计字段**：
   - `changed_files`：代码变更文件列表
   - `diff_summary`：变更摘要
   - `opencode_version`：使用的 OpenCode 版本

2. **工作目录限制**：
   - 必须限制在 `sandbox/workspaces/` 下
   - 通用 shell 工具难以强制此约束（需要额外校验层）

3. **产物差分能力**：
   - 需要执行前后快照对比
   - 通用工具无法自动生成代码变更清单

4. **OpenCode 特定参数解析**：
   - 需要理解 OpenCode 的输出格式
   - 需要适配不同的 output_mode

5. **风险语义明确**：
   - `opencode_run` 的风险语义是“执行编码 Agent 修改代码”
   - 通用 shell 的风险语义是“执行任意命令”，过于宽泛

---

## 审计与产物

### 审计事件

**事件类型**: `tool.opencode_run`

### 记录字段

```json
{
  "timestamp": "ISO 8601 时间戳",
  "event_type": "tool.opencode_run",
  "details": {
    "task_id": "关联的任务ID",
    "step_id": "关联的步骤ID",
    "workspace": "workspace 路径（相对或绝对）",
    "task_prompt": "任务提示（摘要，截断到 200 字符）",
    "output_mode": "diff|inplace|report",
    "timeout_seconds": 300,
    "exit_code": 0,
    "duration_ms": 1234,
    "stdout_len": 1024,
    "stderr_len": 0,
    "changed_files": ["src/main.py", "tests/test_main.py"],
    "changed_files_count": 2,
    "opencode_version": "1.2.3",  // 如可获取
    "evidence_refs": [
      "sandbox/workspaces/xxx_repo/.opencode_output.log",
      "sandbox/workspaces/xxx_repo/.opencode_diff.patch"
    ],
    "approval_id": "approval_xxx",  // 如需要审批
    "risk_level": "R3"
  }
}
```

### 产物差分

**执行前快照**：
- 使用 git 状态（如 workspace 是 git repo）：`git status --porcelain`、`git diff HEAD`
- 或文件系统快照：记录关键文件的 mtime/size/hash

**执行后对比**：
- 优先使用 `git diff`（如适用）
- 或文件系统对比：列出新增/修改/删除的文件

**输出**：
- `changed_files`：变更文件列表（相对路径）
- `diff_summary`：简要变更描述（如 "修改了 2 个文件，新增 10 行，删除 3 行"）
- 完整 diff 写入 `evidence_refs` 中的文件路径

---

## 与 Skills 的结合

### 设计原则

- **Skill 负责流程编排**：定义何时调用 `opencode_run`、如何组织任务提示、如何处理结果
- **执行统一走 Tool**：Skill 生成的 Plan 中包含 `opencode_run` 的调用，由 Tool Runner 执行
- **Skill 不直接执行**：禁止 Skill 脚本直接调用 subprocess，必须通过 Tool 接口

### 示例 Skill（仅描述，不实现）

#### Skill: `opencode_code_review`

**目标**：使用 OpenCode 对指定文件进行代码审查并生成改进建议

**工作流**：
1. 读取待审查文件内容
2. 构建审查提示（如 "审查这个文件的代码质量、性能、安全性问题"）
3. 调用 `opencode_run`（output_mode="report"）
4. 解析 OpenCode 输出，提取审查结果
5. 生成审查报告文件到 sandbox

**Plan 示例**（伪代码）：
```yaml
steps:
  - step_id: "step_1"
    tool_id: "local.file.read"
    params:
      path: "sandbox/workspaces/repo/src/main.py"
  
  - step_id: "step_2"
    tool_id: "opencode_run"
    params:
      workspace_path: "sandbox/workspaces/repo"
      task_prompt: "审查 src/main.py 的代码质量、性能、安全性问题，生成详细报告"
      output_mode: "report"
      timeout_seconds: 300
  
  - step_id: "step_3"
    tool_id: "local.file.write"
    params:
      path: "sandbox/outputs/code_review_report.md"
      content: "${step_2_output_parsed}"
```

#### Skill: `opencode_fix_bug`

**目标**：使用 OpenCode 修复指定 bug

**工作流**：
1. 读取 bug 描述或错误日志
2. 定位相关代码文件
3. 调用 `opencode_run`（output_mode="diff"）生成修复方案
4. 用户审批后，再次调用（output_mode="inplace"）应用修复
5. 验证修复（如运行测试）

**Plan 示例**（伪代码）：
```yaml
steps:
  - step_id: "step_1"
    tool_id: "opencode_run"
    params:
      workspace_path: "sandbox/workspaces/repo"
      task_prompt: "修复以下 bug: ${bug_description}，相关文件: ${bug_file}"
      output_mode: "diff"
    # 此步骤会触发 R3 审批
  
  - step_id: "step_2"  # 审批通过后执行
    tool_id: "opencode_run"
    params:
      workspace_path: "sandbox/workspaces/repo"
      task_prompt: "应用上述修复方案"
      output_mode: "inplace"
    # 此步骤也会触发 R3 审批
```

---

## 验收计划（未来实施时）

### 1. 安装验证

**测试用例**：
- 执行 `opencode --help`，验证命令可用
- 验证版本号输出（如 `opencode --version`）

**通过标准**：
- 命令执行成功，返回码为 0
- 输出包含 OpenCode 的帮助信息

### 2. 最小用例

**测试场景**：
- 在 `sandbox/workspaces/test_repo` 准备一个简单的 Python 文件（如 `hello.py`）
- 调用 `opencode_run`，要求 OpenCode 修改该文件（如添加类型注解）
- 使用 `output_mode="diff"`

**通过标准**：
- Tool 执行成功（exit_code=0 或 OpenCode 的正常退出码）
- 审计日志 `audit.log.jsonl` 中有 `tool.opencode_run` 记录
- `changed_files` 字段包含 `hello.py`
- `evidence_refs` 中包含可访问的日志或 diff 文件

### 3. 审批流程验证

**测试场景**：
- 调用 `opencode_run`（风险等级 R3）
- 验证触发审批流程
- 用户批准后执行
- 用户拒绝后终止

**通过标准**：
- R3 风险触发审批提示
- 审批决策记录到审计日志（`approval_id` 字段）
- 批准后正常执行，拒绝后终止且不修改文件

### 4. 产物差分验证

**测试场景**：
- 执行前后对比 workspace 文件变更
- 验证 `changed_files` 准确性

**通过标准**：
- `changed_files` 列表与实际变更文件一致
- `diff_summary` 或完整 diff 文件可访问
- 执行前后快照对比逻辑正确

### 5. 错误处理验证

**测试场景**：
- OpenCode 执行失败（如语法错误、超时）
- Workspace 路径不存在
- `opencode` 命令不可用

**通过标准**：
- 错误信息记录到 `stderr_excerpt` 和审计日志
- 工具返回 `success=False`，不抛出未捕获异常
- 审计日志记录失败原因

---

## 已知不确定性与待确认事项

### 1. OpenCode CLI 接口兼容性

**问题**：
- OpenCode 是否支持非交互一次性模式（如 `opencode --task "..." --file "..."`）？
- 是否支持 `--output diff|inplace|report` 参数？
- 是否支持通过文件传递任务提示（`--prompt-file`）？

**影响**：
- 若不支持，需要增加驱动适配层：
  - 将任务提示写入临时文件
  - 使用 OpenCode 的实际 CLI 接口
  - 解析输出格式并转换为统一结构

**待确认**：
- 查阅 OpenCode 官方文档或源码，确认 CLI 接口
- 如无官方 CLI，考虑是否需要封装 Python SDK（如有）

### 2. 版本兼容与输出可解析性

**问题**：
- OpenCode 不同版本的 CLI 接口可能变化
- 输出格式（stdout/stderr）可能不一致
- 如何获取 OpenCode 版本号？

**建议**：
- 在 Tool 实现中记录 `opencode_version`（如可获取）
- 对输出格式做容错处理（支持多种格式）
- 在文档中明确支持的版本范围

### 3. 工作目录与 Git 集成

**问题**：
- Workspace 是否需要是 git repo？
- 如需 git 操作（如提交变更），是否在 Tool 内处理还是由 Skill 编排？

**建议**：
- Tool 层不强制 git，但优先使用 git 做差分（如存在）
- Git 提交操作应由 Skill 或独立的 `git_commit` Tool 处理
- Workspace 准备阶段可选择性地初始化或复制 git 仓库

### 4. 并发执行与资源限制

**问题**：
- 多个 `opencode_run` 是否可以并发执行？
- 是否需要限制并发数（避免资源耗尽）？

**建议**：
- v0.1 可先支持串行执行
- 未来如需要并发，在 Tool Runner 层增加并发控制
- 考虑 OpenCode 本身的资源占用（如 LLM API 调用）

### 5. 超时与重试策略

**问题**：
- 默认超时 300 秒是否足够？
- 执行失败是否自动重试？

**建议**：
- 超时时间可配置，默认 300 秒，上限 3600 秒
- v0.1 不自动重试，失败后由用户或 Skill 决定是否重试
- 未来可考虑在 Skill 层实现重试逻辑

---

## 实施优先级

- **P0（必须）**：Tool 基础实现、参数校验、审计日志、风险门控
- **P1（重要）**：产物差分、changed_files 提取、错误处理
- **P2（增强）**：Git 集成优化、输出格式解析增强、版本检测
- **P3（未来）**：并发控制、自动重试、性能优化

---

## 相关文档

- [Tool Contract v0.1](contracts/tool_contract_v0.1.md)
- [Risk Approval Contract v0.1](contracts/risk_approval_v0.1.md)
- [Extension Points](EXTENSION_POINTS.md)
- [README for Contributors](README_FOR_CONTRIBUTORS.md)
