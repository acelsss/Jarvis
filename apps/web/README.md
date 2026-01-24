# Jarvis Web 界面

Jarvis 的现代化 Web 前端界面，采用手绘风格设计（Pencil Sketch Theme）。

## 功能特性

- 💬 **实时对话界面** - 与 Jarvis 进行自然语言交互
- 📊 **任务进度追踪** - 实时查看任务执行状态
- ⚠️ **审批流程** - 高风险操作需要用户确认
- 🛠️ **技能管理** - 查看所有可用技能
- ⚙️ **工具管理** - 查看所有可用工具
- 🔄 **WebSocket 实时更新** - 任务状态实时推送

## 快速开始

### 1. 安装依赖

```bash
pip install fastapi uvicorn websockets python-multipart
```

或者使用项目的可选依赖：

```bash
pip install -e ".[web]"
```

### 2. 启动服务器

```bash
cd /home/jetson/projects/Jarvis
python -m apps.web.api_server
```

服务器将在 `http://localhost:8000` 启动。

### 3. 访问界面

在浏览器中打开 `http://localhost:8000` 即可使用 Web 界面。

## 使用说明

### 发送任务

1. 在聊天输入框中输入你的任务描述
2. 点击发送按钮或按 Enter 键
3. 系统会自动处理任务并显示进度

### 审批高风险操作

如果任务包含高风险操作（R2 或 R3），系统会弹出审批面板：
- 查看计划步骤和风险等级
- 点击"批准"继续执行，或点击"拒绝"取消任务

### 查看技能和工具

- 点击侧边栏的"技能"查看所有可用技能
- 点击侧边栏的"工具"查看所有可用工具

## 技术栈

- **后端**: FastAPI + WebSocket
- **前端**: 原生 HTML/CSS/JavaScript
- **设计风格**: 手绘风格（Pencil Sketch Theme）

## API 端点

- `GET /` - 前端页面
- `POST /api/tasks` - 创建并处理任务
- `POST /api/tasks/{task_id}/approve` - 审批任务
- `GET /api/tasks` - 列出所有任务
- `GET /api/skills` - 列出所有技能
- `GET /api/tools` - 列出所有工具
- `WS /ws` - WebSocket 连接（实时更新）

## 开发

### 修改前端

前端文件位于 `apps/web/frontend/`:
- `index.html` - 主页面结构
- `style.css` - 样式文件（手绘风格）
- `app.js` - 前端逻辑

修改后刷新浏览器即可看到效果。

### 修改后端

后端文件位于 `apps/web/api_server.py`。

修改后需要重启服务器。

## 注意事项

- 确保 Jarvis 的核心依赖已正确安装
- 确保 `identity_pack/` 目录存在且配置正确
- 确保 `skills_workspace/` 目录存在
- WebSocket 连接失败时会自动尝试重连
