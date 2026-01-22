# 完全符合官方设计的实现方案

## 需求分析

用户希望完全符合 Anthropic Agent Skills 官方设计，包括：
1. ✅ Jarvis 可以运行 py 脚本（skill 文件夹中的脚本）
2. ✅ 执行 skill 过程中可以询问问题（交互式执行）

---

## 可行性分析

### ✅ 需求 1：运行 py 脚本

**可行性：完全可行**

**当前状态**：
- `ShellTool` 只允许 `echo` 命令
- 有完整的风险控制和审批机制
- 有沙箱目录隔离

**实现难度**：中等
- 需要扩展 `ShellTool` 或创建新的 `ScriptTool`
- 需要安全机制（白名单、沙箱、权限控制）
- 需要风险评估机制

---

### ✅ 需求 2：执行过程中询问问题

**可行性：完全可行**

**当前状态**：
- 路由阶段支持 "clarify" 类型询问问题
- 执行阶段是"一次性"的，不会中途暂停
- 有任务状态管理机制

**实现难度**：较高
- 需要修改执行流程，支持"暂停-询问-继续"
- 需要交互式执行机制
- 需要任务状态管理（RUNNING → WAITING_INPUT → RUNNING）

---

## 实现方案

### 方案 1：运行 py 脚本

#### 1.1 方案 A：扩展 ShellTool（推荐）

**优点**：
- 复用现有工具
- 统一的风险控制机制
- 代码改动最小

**实现步骤**：

1. **扩展 ShellTool 允许的命令白名单**
   ```python
   # tools/local/shell_tool.py
   class ShellTool(Tool):
       # 允许的命令白名单
       ALLOWED_COMMANDS = [
           "echo",
           "python3",  # 新增：允许执行 Python 脚本
       ]
       
       # 允许的脚本路径白名单（仅限 skills_workspace）
       ALLOWED_SCRIPT_PATHS = [
           "skills_workspace/",  # 只允许执行技能目录中的脚本
       ]
       
       def _is_allowed(self, command: str) -> bool:
           """检查命令是否允许执行。"""
           command_lower = command.strip().lower()
           
           # 检查是否以允许的命令开头
           for allowed in self.ALLOWED_COMMANDS:
               if command_lower.startswith(allowed):
                   # 如果是 python3，检查脚本路径
                   if allowed == "python3":
                       return self._is_script_path_allowed(command)
                   return True
           return False
       
       def _is_script_path_allowed(self, command: str) -> bool:
           """检查脚本路径是否在白名单中。"""
           # 解析命令，提取脚本路径
           # 例如: "python3 skills_workspace/my-skill/scripts/init.py"
           import re
           match = re.search(r'python3\s+([^\s]+)', command)
           if match:
               script_path = match.group(1)
               # 检查是否在允许的路径中
               for allowed_path in self.ALLOWED_SCRIPT_PATHS:
                   if script_path.startswith(allowed_path):
                       return True
           return False
   ```

2. **设置风险等级**
   ```python
   # 执行脚本的风险等级：R2（需要审批）
   risk_level=RISK_LEVEL_R2,
   requires_approval=True,
   ```

3. **更新 Planner 系统提示**
   ```python
   # core/orchestrator/planner.py
   system = "...\n"
   "重要：对于 shell 工具，支持以下操作：\n"
   '  - "command": "echo <text>" - 输出文本\n'
   '  - "command": "python3 <script_path>" - 执行 Python 脚本（仅限 skills_workspace 中的脚本）\n'
   "    示例: python3 skills_workspace/skill-creator/scripts/init_skill.py my-skill --path skills_workspace/\n"
   ```

#### 1.2 方案 B：创建新的 ScriptTool

**优点**：
- 更清晰的职责分离
- 可以针对脚本执行做专门优化
- 更容易扩展（支持其他脚本语言）

**缺点**：
- 需要创建新工具
- 代码重复（风险控制逻辑）

**实现步骤**：

1. **创建 `tools/local/script_tool.py`**
   ```python
   class ScriptTool(Tool):
       """脚本执行工具（仅限 skills_workspace 中的脚本）。"""
       
       def __init__(self):
           super().__init__(
               tool_id="script",
               name="Script Executor",
               description="执行技能目录中的脚本（Python/Bash等）",
               parameters={
                   "type": "object",
                   "properties": {
                       "script_path": {"type": "string", "description": "脚本路径（相对于项目根目录）"},
                       "args": {"type": "array", "description": "脚本参数"},
                   },
                   "required": ["script_path"],
               },
               risk_level=RISK_LEVEL_R2,
               requires_approval=True,
           )
       
       def _is_allowed(self, script_path: str) -> bool:
           """检查脚本路径是否允许执行。"""
           # 只允许执行 skills_workspace 中的脚本
           return script_path.startswith("skills_workspace/")
       
       async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
           script_path = params.get("script_path")
           args = params.get("args", [])
           
           if not self._is_allowed(script_path):
               raise ValueError(f"不允许执行此脚本: {script_path}")
           
           # 构建命令
           command = f"python3 {script_path} {' '.join(args)}"
           
           # 执行命令
           process = await asyncio.create_subprocess_shell(
               command,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           stdout, stderr = await process.communicate()
           
           return {
               "exit_code": process.returncode,
               "stdout": stdout.decode("utf-8"),
               "stderr": stderr.decode("utf-8"),
               "script_path": script_path,
           }
   ```

2. **注册新工具**
   ```python
   # apps/cli/main.py
   script_tool = ScriptTool()
   tool_registry.register(script_tool)
   ```

**推荐方案**：方案 A（扩展 ShellTool）
- 代码改动最小
- 复用现有机制
- 更容易维护

---

### 方案 2：执行过程中询问问题

#### 2.1 架构设计

**核心思路**：
- 在执行过程中，如果 LLM 需要更多信息，可以"暂停"执行
- 通过特殊的工具调用（如 `ask_question`）来询问用户
- 用户回答后，继续执行

#### 2.2 实现方案

##### 方案 A：通过特殊工具 `ask_question`（推荐）

**优点**：
- 符合现有工具架构
- LLM 可以在计划中主动添加询问步骤
- 统一的风险控制和审计

**实现步骤**：

1. **创建 `AskQuestionTool`**
   ```python
   # tools/local/ask_question_tool.py
   class AskQuestionTool(Tool):
       """询问问题工具（用于执行过程中询问用户）。"""
       
       def __init__(self):
           super().__init__(
               tool_id="ask_question",
               name="Ask Question",
               description="在执行过程中询问用户问题",
               parameters={
                   "type": "object",
                   "properties": {
                       "question": {"type": "string", "description": "要询问的问题"},
                       "context": {"type": "string", "description": "问题上下文（可选）"},
                   },
                   "required": ["question"],
               },
               risk_level=RISK_LEVEL_R0,  # 询问问题无风险
               requires_approval=False,
           )
       
       async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
           """执行询问（会暂停执行，等待用户输入）。"""
           question = params.get("question", "")
           context = params.get("context", "")
           
           # 抛出特殊异常，让执行器知道需要暂停
           raise UserInputRequired(question=question, context=context)
   ```

2. **定义异常类**
   ```python
   # core/contracts/exceptions.py
   class UserInputRequired(Exception):
       """需要用户输入时抛出此异常。"""
       
       def __init__(self, question: str, context: str = ""):
           self.question = question
           self.context = context
           super().__init__(f"需要用户输入: {question}")
   ```

3. **修改执行流程**
   ```python
   # apps/cli/main.py
   for i, step in enumerate(plan.steps, 1):
       try:
           tool_result = await tool_runner.run(tool, step.step_id, step.params)
       except UserInputRequired as e:
           # 暂停执行，询问用户
           print(f"\n❓ {e.question}")
           if e.context:
               print(f"   上下文: {e.context}")
           
           # 更新任务状态
           task.update_status(TASK_STATUS_WAITING_INPUT)
           task_manager.update_task(task, extra_info={
               "waiting_for_input": {
                   "question": e.question,
                   "context": e.context,
                   "step_id": step.step_id,
               }
           })
           
           # 获取用户输入
           user_answer = input("\n请输入回答: ").strip()
           
           # 将用户回答添加到任务上下文
           task.context["user_inputs"] = task.context.get("user_inputs", [])
           task.context["user_inputs"].append({
               "question": e.question,
               "answer": user_answer,
               "step_id": step.step_id,
           })
           
           # 继续执行（重新执行当前步骤，但这次传入用户回答）
           # 或者：LLM 重新生成计划，包含用户回答
           task.update_status(TASK_STATUS_RUNNING)
           continue
   ```

4. **更新 Planner 系统提示**
   ```python
   # core/orchestrator/planner.py
   system = "...\n"
   "如果执行过程中需要更多信息，可以使用 ask_question 工具询问用户：\n"
   '  - "tool_id": "ask_question"\n'
   '  - "params": {"question": "你的问题", "context": "上下文（可选）"}\n'
   "执行会在询问时暂停，等待用户回答后继续。\n"
   ```

5. **添加任务状态**
   ```python
   # core/contracts/task.py
   TASK_STATUS_WAITING_INPUT = "waiting_input"  # 等待用户输入
   ```

##### 方案 B：通过 LLM 主动生成询问步骤

**优点**：
- LLM 可以在计划中主动添加询问步骤
- 不需要特殊工具
- 更灵活

**缺点**：
- 需要 LLM 理解何时需要询问
- 可能不够直观

**实现步骤**：

1. **在计划生成时，LLM 可以添加询问步骤**
   ```json
   {
     "steps": [
       {
         "tool_id": "ask_question",
         "description": "询问用户：技能应该支持什么功能？",
         "params": {
           "question": "技能应该支持什么功能？编辑、旋转，还有其他吗？",
           "context": "正在创建图像编辑器技能"
         }
       },
       {
         "tool_id": "file",
         "description": "根据用户回答创建 SKILL.md",
         "params": {...}
       }
     ]
   }
   ```

2. **执行时处理询问步骤**
   ```python
   if step.tool_id == "ask_question":
       question = step.params.get("question")
       context = step.params.get("context", "")
       
       print(f"\n❓ {question}")
       if context:
           print(f"   上下文: {context}")
       
       user_answer = input("\n请输入回答: ").strip()
       
       # 将回答保存到任务上下文
       task.context["last_answer"] = user_answer
       
       # 继续执行下一步
       continue
   ```

**推荐方案**：方案 A（通过特殊工具）
- 更符合工具架构
- 更容易扩展
- 统一的风险控制

---

## 完整实现流程

### 阶段 1：运行 py 脚本

1. ✅ 扩展 `ShellTool` 支持 `python3` 命令
2. ✅ 添加脚本路径白名单检查
3. ✅ 设置风险等级为 R2（需要审批）
4. ✅ 更新 Planner 系统提示
5. ✅ 测试执行 `init_skill.py` 等脚本

### 阶段 2：执行过程中询问问题

1. ✅ 创建 `AskQuestionTool`
2. ✅ 定义 `UserInputRequired` 异常
3. ✅ 添加 `TASK_STATUS_WAITING_INPUT` 状态
4. ✅ 修改执行流程，支持暂停和继续
5. ✅ 更新 Planner 系统提示
6. ✅ 测试交互式执行

---

## 风险评估

### 运行 py 脚本的风险

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| 恶意脚本执行 | 高 | 白名单限制（仅 skills_workspace） |
| 系统资源消耗 | 中 | 超时控制、资源限制 |
| 文件系统破坏 | 中 | 沙箱隔离、权限控制 |
| 网络访问 | 中 | 网络隔离（可选） |

**缓解措施**：
- ✅ 只允许执行 `skills_workspace/` 中的脚本
- ✅ 需要用户审批（R2 风险等级）
- ✅ 在沙箱中执行（可选）
- ✅ 超时控制（默认 30 秒）

### 询问问题的风险

| 风险 | 等级 | 缓解措施 |
|------|------|----------|
| 执行流程中断 | 低 | 状态管理、恢复机制 |
| 用户输入验证 | 低 | 输入验证、错误处理 |

**缓解措施**：
- ✅ 任务状态管理（WAITING_INPUT → RUNNING）
- ✅ 用户输入验证
- ✅ 错误处理和恢复机制

---

## 测试计划

### 测试 1：运行 py 脚本

```bash
# 测试执行 init_skill.py
python3 -m apps.cli.main "我想创建一个新的技能 test-skill，请使用 init_skill.py 初始化"
```

**预期结果**：
- ✅ 路由到 skill-creator
- ✅ LLM 生成包含 `shell` 工具的计划
- ✅ 需要用户审批（R2 风险）
- ✅ 执行 `python3 skills_workspace/skill-creator/scripts/init_skill.py test-skill --path skills_workspace/`
- ✅ 成功创建技能目录

### 测试 2：执行过程中询问问题

```bash
# 测试交互式执行
python3 -m apps.cli.main "我想创建一个新的技能，但我不知道应该支持什么功能"
```

**预期结果**：
- ✅ 路由到 skill-creator
- ✅ LLM 生成包含 `ask_question` 步骤的计划
- ✅ 执行暂停，显示问题
- ✅ 用户回答后继续执行
- ✅ 根据用户回答创建技能

---

## 总结

### ✅ 可行性

1. **运行 py 脚本**：✅ 完全可行
   - 实现难度：中等
   - 风险：可控（通过白名单和审批）
   - 推荐方案：扩展 `ShellTool`

2. **执行过程中询问问题**：✅ 完全可行
   - 实现难度：较高
   - 风险：低
   - 推荐方案：通过 `AskQuestionTool` 工具

### 📋 实现优先级

1. **高优先级**：运行 py 脚本
   - 直接影响 skill-creator 的完整性
   - 实现相对简单

2. **中优先级**：执行过程中询问问题
   - 提升用户体验
   - 实现相对复杂

### ⚠️ 注意事项

1. **安全性**：脚本执行需要严格的白名单和审批机制
2. **用户体验**：询问问题需要清晰的提示和错误处理
3. **兼容性**：确保不影响现有功能

---

## 下一步

1. 确认方案可行性
2. 确认实现优先级
3. 开始实现（如果确认）
