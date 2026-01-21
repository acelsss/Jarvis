# Jarvis v0.1 - Kernel MVP 运行说明

## 快速开始

### 1. 安装依赖

```bash
cd /home/jetson/projects/Jarvis
pip install -e .
```

或者直接安装 pyyaml：

```bash
pip install pyyaml
```

### 2. 运行 CLI

```bash
python -m apps.cli.main
```

或者直接传入任务描述：

```bash
python -m apps.cli.main "创建一个测试文件"
```

## 运行流程说明

### 完整闭环流程

1. **CLI 输入** - 接收用户任务描述
2. **创建任务** - 生成唯一任务ID，状态: `new`
3. **构建上下文** - 读取 `identity_pack/` 配置 + OpenMemory stub 搜索（top-3）
4. **路由任务** - 简单规则路由到合适的工具
5. **生成计划** - Planner 生成 2-3 个 PlanStep（至少包含 1 个 file_tool）
6. **风险评估** - 检查是否有 R2 及以上风险等级
7. **审批流程** - 如需要，CLI 提示用户 yes/no 决策
8. **执行工具** - ToolRunner 统一执行并记录 ToolResult
9. **记录审计** - 所有操作写入 `memory/raw_logs/audit.log.jsonl`
10. **输出总结** - 显示 task_id、执行的工具、产物路径

### 产物位置

- **沙箱文件**: `./sandbox/` 目录（可配置）
- **审计日志**: `./memory/raw_logs/audit.log.jsonl`

### 配置说明

- `identity_pack/preferences.yaml` - 配置 sandbox_root 等参数
- `.env` - 环境变量（可选，支持 SANDBOX_ROOT）

## LLM 配置

LLM 用于“路由/规划”阶段的智能补充，执行仍严格走审批与审计流程；未配置 key 也可正常运行。

### OpenAI-Compatible（含国内兼容服务）

- 设置 `LLM_PROVIDER=openai`
- 配置 `OPENAI_API_KEY`
- 国内兼容服务：修改 `OPENAI_BASE_URL` 指向对应服务地址
- 可选设置 `OPENAI_MODEL`

### Gemini

- 设置 `LLM_PROVIDER=gemini`
- 配置 `GEMINI_API_KEY`
- 可选设置 `GEMINI_MODEL`

### 开关说明

- `LLM_ENABLE_ROUTER=1` 启用 LLM 路由（规则优先）
- `LLM_ENABLE_PLANNER=1` 启用 LLM 规划（JSON 步骤结构）

## 示例运行输出

见下方示例。
