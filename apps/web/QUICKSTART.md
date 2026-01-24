# Jarvis Web 界面快速开始

## 一键启动

```bash
# 方法1: 使用启动脚本
./apps/web/start.sh

# 方法2: 直接运行
python -m apps.web.api_server
```

## 安装依赖

如果还没有安装 Web 依赖，请先安装：

```bash
pip install fastapi uvicorn websockets python-multipart
```

或者使用项目的可选依赖：

```bash
pip install -e ".[web]"
```

## 访问界面

启动后，在浏览器中打开：

```
http://localhost:8000
```

## 功能演示

1. **发送任务**: 在输入框中输入任务描述，例如：
   - "创建一个测试文件"
   - "列出当前目录的文件"
   - "帮我写一个Python脚本"

2. **查看进度**: 任务执行过程中会实时显示进度

3. **审批操作**: 如果任务包含高风险操作，会弹出审批面板

4. **查看技能和工具**: 点击侧边栏查看所有可用的技能和工具

## 界面特色

- 🎨 **手绘风格设计** - 采用 Pencil Sketch 主题，界面简洁优雅
- 💬 **实时对话** - 与 Jarvis 进行自然语言交互
- 📊 **进度追踪** - 实时查看任务执行状态
- ⚠️ **安全审批** - 高风险操作需要确认
- 🔄 **实时更新** - WebSocket 推送任务状态

## 故障排除

### 端口被占用

如果 8000 端口被占用，可以修改端口：

```python
# 在 api_server.py 最后修改
uvicorn.run(app, host="0.0.0.0", port=8080)
```

### 静态文件无法加载

确保 `apps/web/frontend/` 目录存在且包含以下文件：
- `index.html`
- `style.css`
- `app.js`

### WebSocket 连接失败

检查防火墙设置，确保 WebSocket 连接未被阻止。
