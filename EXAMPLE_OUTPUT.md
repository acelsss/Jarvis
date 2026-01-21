# Jarvis v0.1 - 示例运行输出

## 示例 1: 低风险任务（自动批准）

```bash
$ python -m apps.cli.main "创建一个测试文件并写入内容"
```

**输出：**

```
============================================================
Jarvis v0.1 - Kernel MVP
============================================================

[1/8] 接收任务: 创建一个测试文件并写入内容
[2/8] 任务已创建: task_abc123-def456-ghi789
[3/8] 构建上下文...
  - 身份配置已加载
  - OpenMemory 搜索结果: 0 条
[4/8] 路由任务到工具...
  - 路由结果: file, shell
[5/8] 生成执行计划...
  - 计划ID: plan_xyz789-uvw456-rst123
  - 步骤数: 2
    1. file - 创建任务产物文件: task_abc123-def456-ghi789.txt (风险: R1)
    2. file - 创建任务摘要文件: task_abc123-def456-ghi789_summary.txt (风险: R1)
[6/8] 风险评估...
  - 风险等级: R1
  - 需要审批: False
  - 自动批准（低风险）

[7/8] 执行工具...

  步骤 1/2: file
    描述: 创建任务产物文件: task_abc123-def456-ghi789.txt
    ✓ 执行成功
    📄 产物: /home/jetson/projects/Jarvis/sandbox/task_abc123-def456-ghi789.txt

  步骤 2/2: file
    描述: 创建任务摘要文件: task_abc123-def456-ghi789_summary.txt
    ✓ 执行成功
    📄 产物: /home/jetson/projects/Jarvis/sandbox/task_abc123-def456-ghi789_summary.txt

============================================================
[8/8] 任务完成总结
============================================================
任务ID: task_abc123-def456-ghi789
状态: completed
执行的工具: file, file
产物路径:
  - /home/jetson/projects/Jarvis/sandbox/task_abc123-def456-ghi789.txt
  - /home/jetson/projects/Jarvis/sandbox/task_abc123-def456-ghi789_summary.txt
审批记录: approval_xxx111-yyy222-zzz333
审计日志: memory/raw_logs/audit.log.jsonl
============================================================
```

## 示例 2: 高风险任务（需要审批）

```bash
$ python -m apps.cli.main "执行shell命令"
```

**输出：**

```
============================================================
Jarvis v0.1 - Kernel MVP
============================================================

[1/8] 接收任务: 执行shell命令
[2/8] 任务已创建: task_aaa111-bbb222-ccc333
[3/8] 构建上下文...
  - 身份配置已加载
  - OpenMemory 搜索结果: 0 条
[4/8] 路由任务到工具...
  - 路由结果: shell, file
[5/8] 生成执行计划...
  - 计划ID: plan_ddd444-eee555-fff666
  - 步骤数: 3
    1. file - 创建任务产物文件: task_aaa111-bbb222-ccc333.txt (风险: R1)
    2. shell - 执行工具: shell (风险: R2)
    3. file - 创建任务摘要文件: task_aaa111-bbb222-ccc333_summary.txt (风险: R1)
[6/8] 风险评估...
  - 风险等级: R2
  - 需要审批: True

⚠️  检测到风险等级 R2，需要审批。是否批准执行? (yes/no): yes
✓ 已批准

[7/8] 执行工具...

  步骤 1/3: file
    描述: 创建任务产物文件: task_aaa111-bbb222-ccc333.txt
    ✓ 执行成功
    📄 产物: /home/jetson/projects/Jarvis/sandbox/task_aaa111-bbb222-ccc333.txt

  步骤 2/3: shell
    描述: 执行工具: shell
    ✓ 执行成功

  步骤 3/3: file
    描述: 创建任务摘要文件: task_aaa111-bbb222-ccc333_summary.txt
    ✓ 执行成功
    📄 产物: /home/jetson/projects/Jarvis/sandbox/task_aaa111-bbb222-ccc333_summary.txt

============================================================
[8/8] 任务完成总结
============================================================
任务ID: task_aaa111-bbb222-ccc333
状态: completed
执行的工具: file, shell, file
产物路径:
  - /home/jetson/projects/Jarvis/sandbox/task_aaa111-bbb222-ccc333.txt
  - /home/jetson/projects/Jarvis/sandbox/task_aaa111-bbb222-ccc333_summary.txt
审批记录: approval_ggg777-hhh888-iii999
审计日志: memory/raw_logs/audit.log.jsonl
============================================================
```

## 示例 3: 用户拒绝审批

```bash
$ python -m apps.cli.main "执行shell命令"
```

**输出（部分）：**

```
...
[6/8] 风险评估...
  - 风险等级: R2
  - 需要审批: True

⚠️  检测到风险等级 R2，需要审批。是否批准执行? (yes/no): no
✗ 已拒绝，任务终止
```

## 审计日志示例 (audit.log.jsonl)

```jsonl
{"timestamp": "2024-01-01T12:00:00.123456", "event_type": "task_created", "details": {"task_id": "task_abc123", "description": "创建一个测试文件", "status": "new"}}
{"timestamp": "2024-01-01T12:00:01.234567", "event_type": "context_built", "details": {"task_id": "task_abc123", "openmemory_results_count": 0}}
{"timestamp": "2024-01-01T12:00:02.345678", "event_type": "plan_created", "details": {"task_id": "task_abc123", "plan_id": "plan_xyz789", "steps_count": 2}}
{"timestamp": "2024-01-01T12:00:03.456789", "event_type": "task_auto_approved", "details": {"approval_id": "approval_xxx111", "task_id": "task_abc123", "risk_level": "R1"}}
{"timestamp": "2024-01-01T12:00:04.567890", "event_type": "task_started", "details": {"task_id": "task_abc123"}}
{"timestamp": "2024-01-01T12:00:05.678901", "event_type": "tool_executed", "details": {"task_id": "task_abc123", "step_id": "step_aaa111", "tool_id": "file", "success": true, "evidence_refs": ["/path/to/sandbox/task_abc123.txt"]}}
{"timestamp": "2024-01-01T12:00:06.789012", "event_type": "task_completed", "details": {"task_id": "task_abc123", "artifacts": ["/path/to/sandbox/task_abc123.txt"], "executed_tools": ["file"]}}
```

## 生成的文件示例

### sandbox/task_abc123-def456-ghi789.txt

```
任务: 创建一个测试文件并写入内容
创建时间: 2024-01-01T12:00:05.678901
任务ID: task_abc123-def456-ghi789
```

### sandbox/task_abc123-def456-ghi789_summary.txt

```
任务摘要
任务ID: task_abc123-def456-ghi789
描述: 创建一个测试文件并写入内容
状态: completed
```
