# Skills 子系统使用说明 v0.1

## 概述

Skills 子系统允许通过定义技能文件来自动生成任务执行计划。v0.1 版本支持 Claude Code 风格的 SKILL.md 格式。

## 功能特性

1. **技能注册** - 自动扫描 `skills_workspace/` 目录，加载所有技能
2. **技能解析** - 解析 YAML frontmatter + Markdown body 格式的 SKILL.md
3. **计划生成** - 将技能指令转换为可执行的 PlanStep
4. **智能路由** - 根据任务描述自动匹配技能
5. **安全执行** - v0.1 禁止技能执行脚本，只通过 ToolRunner 执行受控工具

## 技能文件格式

技能文件应放在 `skills_workspace/{skill_id}/SKILL.md`，格式如下：

```markdown
---
name: 技能名称
description: 技能描述
tags:
  - tag1
  - tag2
version: 0.1.0
author: 作者名
---

# 技能标题

## 功能说明

技能的功能说明...

## 执行步骤

1. 步骤1描述
2. 步骤2描述
3. 步骤3描述
```

### 必需字段

- `name`: 技能名称
- `description`: 技能描述
- `tags`: 标签列表（用于匹配）

### 可选字段

- `version`: 版本号
- `author`: 作者
- 其他自定义字段

## 使用方式

### 1. 查看已加载的技能

```bash
python -m apps.cli.main
# 输入: /skills
```

输出示例：
```
============================================================
已加载的技能列表
============================================================

技能ID: wechat_article
  名称: 微信公众号文章生成
  描述: 根据用户输入的主题，生成一篇结构化的微信公众号文章，包含标题、摘要、正文和结尾。
  标签: content, article, wechat, writing
  路径: skills_workspace/wechat_article/SKILL.md

============================================================
```

### 2. 触发技能执行

当任务描述包含技能名称或标签时，系统会自动匹配并使用该技能生成计划：

```bash
python -m apps.cli.main "生成一篇关于Python的微信公众号文章"
```

系统会：
1. 匹配到 `wechat_article` 技能（因为包含"微信公众号文章"）
2. 使用 `skill_to_plan` 将技能的 instructions_md 转换为 PlanStep
3. 每个步骤使用 file_tool 保存中间结果
4. 最终生成完整的文章文件

### 3. 技能匹配规则

Router 会按以下规则匹配技能：

1. **名称匹配** - 任务描述包含技能名称
2. **标签匹配** - 任务描述包含技能标签

匹配优先级：技能 > 工具

## 计划生成逻辑

`skill_to_plan` 函数将技能的 `instructions_md` 转换为 PlanStep：

1. **段落分割** - 按 Markdown 标题或空行分割指令
2. **步骤创建** - 每个段落创建一个 PlanStep
3. **文件保存** - 每个步骤使用 file_tool 保存中间结果到 sandbox
4. **风险等级** - 默认所有步骤风险等级为 R1

生成的计划包含：
- 多个中间步骤文件（`{task_id}_skill_{skill_id}_step{N}.md`）
- 一个总结文件（`{task_id}_skill_{skill_id}_summary.md`）
- 一个最终产物文件（`{task_id}_skill_{skill_id}_final.md`）

## 示例技能

### wechat_article

位置：`skills_workspace/wechat_article/SKILL.md`

功能：生成微信公众号文章

匹配关键词：
- "微信公众号文章"
- "文章"
- "content", "article", "wechat", "writing" (标签)

## 添加新技能

1. 在 `skills_workspace/` 下创建新目录：`skills_workspace/{skill_id}/`
2. 创建 `SKILL.md` 文件，包含 YAML frontmatter 和 Markdown body
3. 重启 CLI，系统会自动扫描并加载新技能

示例：

```bash
mkdir -p skills_workspace/my_skill
cat > skills_workspace/my_skill/SKILL.md << 'EOF'
---
name: 我的技能
description: 技能描述
tags:
  - tag1
  - tag2
---

# 我的技能

## 功能说明

...

## 执行步骤

1. 步骤1
2. 步骤2
EOF
```

## 约束说明

v0.1 版本的约束：

1. **禁止脚本执行** - 技能不能直接执行任何脚本
2. **仅转 Plan** - 技能只能转换为 PlanStep，最终通过 ToolRunner 执行
3. **受控工具** - 只能使用已注册的工具（file_tool, shell_tool 等）
4. **文件输出** - 所有产物必须通过 file_tool 写入 sandbox

## 技术实现

### 核心组件

- `skills/registry.py` - 技能注册表，扫描工作空间
- `skills/adapters/claude_code_adapter.py` - 解析 SKILL.md
- `skills/runtime/to_plan.py` - 转换 instructions 为 Plan
- `core/router/route.py` - 技能匹配路由

### 数据流

```
CLI 输入 → Router 匹配技能 → skill_to_plan → PlanStep[] → ToolRunner → 文件产物
```

## 未来扩展

- [ ] 支持 Agent Skills 格式
- [ ] 技能参数化（支持用户输入参数）
- [ ] 技能组合（多个技能串联）
- [ ] 技能版本管理
- [ ] 技能依赖关系
