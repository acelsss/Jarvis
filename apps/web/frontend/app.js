// Jarvis 前端应用
class JarvisApp {
    constructor() {
        this.apiBase = '/api';
        // 根据当前协议自动选择 ws 或 wss
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.wsUrl = `${protocol}//${window.location.host}/ws`;
        this.ws = null;
        this.currentTaskId = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.connectWebSocket();
        this.loadSkills();
        this.loadTools();
        this.setupChatInput();
    }

    setupEventListeners() {
        // 导航切换
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const view = e.currentTarget.dataset.view;
                this.switchView(view);
            });
        });

        // 发送消息
        const sendBtn = document.getElementById('btn-send');
        const chatInput = document.getElementById('chat-input');
        
        sendBtn.addEventListener('click', () => this.sendMessage());
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // 清空对话
        document.getElementById('clear-chat').addEventListener('click', () => {
            this.clearChat();
        });

        // 关闭进度
        document.getElementById('close-progress').addEventListener('click', () => {
            document.getElementById('task-progress').style.display = 'none';
        });

        // 审批按钮
        document.getElementById('btn-approve').addEventListener('click', () => {
            this.approveTask(true);
        });
        document.getElementById('btn-reject').addEventListener('click', () => {
            this.approveTask(false);
        });
    }

    setupChatInput() {
        const chatInput = document.getElementById('chat-input');
        chatInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
    }

    switchView(viewName) {
        // 更新导航状态
        document.querySelectorAll('.nav-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-view="${viewName}"]`).classList.add('active');

        // 更新视图显示
        document.querySelectorAll('.view').forEach(view => {
            view.classList.remove('active');
        });
        document.getElementById(`${viewName}-view`).classList.add('active');
    }

    connectWebSocket() {
        try {
            this.ws = new WebSocket(this.wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket 连接已建立');
                this.updateConnectionStatus(true);
            };

            this.ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                this.handleWebSocketMessage(message);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket 错误:', error);
                this.updateConnectionStatus(false);
            };

            this.ws.onclose = () => {
                console.log('WebSocket 连接已关闭');
                this.updateConnectionStatus(false);
                // 尝试重连
                setTimeout(() => this.connectWebSocket(), 3000);
            };
        } catch (error) {
            console.error('WebSocket 连接失败:', error);
            this.updateConnectionStatus(false);
        }
    }

    updateConnectionStatus(connected) {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');
        
        if (connected) {
            statusDot.style.background = '#10b981';
            statusText.textContent = '已连接';
        } else {
            statusDot.style.background = '#ef4444';
            statusText.textContent = '未连接';
        }
    }

    handleWebSocketMessage(message) {
        if (message.type === 'task_update') {
            this.handleTaskUpdate(message.stage, message.data);
        }
    }

    async sendMessage() {
        const input = document.getElementById('chat-input');
        const message = input.value.trim();
        
        if (!message) return;

        // 添加用户消息到界面
        this.addMessage('user', message);
        input.value = '';
        input.style.height = 'auto';

        // 禁用发送按钮
        const sendBtn = document.getElementById('btn-send');
        sendBtn.disabled = true;

        try {
            const response = await fetch(`${this.apiBase}/tasks`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ description: message }),
            });

            const result = await response.json();

            if (result.status === 'waiting_approval') {
                this.currentTaskId = result.task_id;
                this.showApprovalPanel(result);
            } else if (result.qa) {
                this.addMessage('assistant', result.answer);
            } else {
                this.addMessage('assistant', result.summary || '任务已完成');
            }
        } catch (error) {
            console.error('发送消息失败:', error);
            this.addMessage('assistant', '抱歉，处理任务时出现错误。请稍后重试。');
        } finally {
            sendBtn.disabled = false;
        }
    }

    handleTaskUpdate(stage, data) {
        const progressPanel = document.getElementById('task-progress');
        const progressSteps = document.getElementById('progress-steps');

        // 显示进度面板
        if (progressPanel.style.display === 'none') {
            progressPanel.style.display = 'block';
        }

        // 更新步骤
        let stepHtml = '';

        const stages = [
            { key: 'received', label: '接收任务', icon: '📥' },
            { key: 'task_created', label: '创建任务', icon: '✨' },
            { key: 'building_context', label: '构建上下文', icon: '🔍' },
            { key: 'context_built', label: '上下文就绪', icon: '✓' },
            { key: 'routing', label: '路由任务', icon: '🧭' },
            { key: 'routed', label: '路由完成', icon: '📍' },
            { key: 'planning', label: '生成计划', icon: '📝' },
            { key: 'planned', label: '计划就绪', icon: '✅' },
            { key: 'executing', label: '执行中', icon: '⚙️' },
            { key: 'completed', label: '已完成', icon: '🎉' },
        ];

        const currentStageIndex = stages.findIndex(s => s.key === stage);
        
        stages.forEach((stageInfo, index) => {
            let status = '';
            if (index < currentStageIndex) {
                status = 'completed';
            } else if (index === currentStageIndex) {
                status = 'active';
            }

            stepHtml += `
                <div class="progress-step ${status}">
                    <div class="progress-step-icon">${status === 'completed' ? '✓' : status === 'active' ? '⟳' : '○'}</div>
                    <div class="progress-step-text">${stageInfo.label}</div>
                </div>
            `;
        });

        progressSteps.innerHTML = stepHtml;

        // 如果完成，添加详细信息
        if (stage === 'completed' && data.artifacts) {
            setTimeout(() => {
                let artifactsHtml = '<div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-color);">';
                artifactsHtml += '<strong>生成的文件:</strong><ul style="margin-top: 8px; padding-left: 20px;">';
                data.artifacts.forEach(art => {
                    artifactsHtml += `<li style="margin-bottom: 4px;"><code style="background: var(--bg-color); padding: 2px 6px; border-radius: 4px;">${art.path}</code></li>`;
                });
                artifactsHtml += '</ul></div>';
                progressSteps.innerHTML += artifactsHtml;
            }, 500);
        }
    }

    showApprovalPanel(data) {
        const panel = document.getElementById('approval-panel');
        const stepsDiv = document.getElementById('approval-steps');
        
        let stepsHtml = '';
        if (data.steps) {
            data.steps.forEach(step => {
                stepsHtml += `
                    <div class="approval-step">
                        ${step.description}
                        <span class="risk-badge ${step.risk_level}">${step.risk_level}</span>
                    </div>
                `;
            });
        }
        stepsDiv.innerHTML = stepsHtml;
        panel.style.display = 'block';
    }

    async approveTask(approved) {
        if (!this.currentTaskId) return;

        const panel = document.getElementById('approval-panel');
        panel.style.display = 'none';

        try {
            const response = await fetch(`${this.apiBase}/tasks/${this.currentTaskId}/approve`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    task_id: this.currentTaskId,
                    approved: approved,
                }),
            });

            const result = await response.json();

            if (approved && result.status === 'completed') {
                this.addMessage('assistant', result.summary || '任务已执行完成');
            } else {
                this.addMessage('assistant', '任务已取消');
            }
        } catch (error) {
            console.error('审批失败:', error);
            this.addMessage('assistant', '审批操作失败，请稍后重试。');
        }

        this.currentTaskId = null;
    }

    addMessage(role, text) {
        const messagesContainer = document.getElementById('chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;

        const time = new Date().toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        messageDiv.innerHTML = `
            <div class="message-avatar">${role === 'user' ? '👤' : '🤖'}</div>
            <div class="message-content">
                <div class="message-text">${this.escapeHtml(text)}</div>
                <div class="message-time">${time}</div>
            </div>
        `;

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    clearChat() {
        const messagesContainer = document.getElementById('chat-messages');
        messagesContainer.innerHTML = `
            <div class="message assistant">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    <div class="message-text">
                        你好！我是 Jarvis，你的智能助理。我可以帮你处理各种任务，包括文件操作、代码执行、问题回答等。
                    </div>
                    <div class="message-time">刚刚</div>
                </div>
            </div>
        `;
    }

    async loadSkills() {
        try {
            const response = await fetch(`${this.apiBase}/skills`);
            const data = await response.json();
            
            const skillsGrid = document.getElementById('skills-grid');
            if (data.skills && data.skills.length > 0) {
                skillsGrid.innerHTML = data.skills.map(skill => `
                    <div class="skill-card">
                        <div class="skill-card-header">
                            <div class="skill-icon">🛠️</div>
                            <div>
                                <div class="skill-name">${this.escapeHtml(skill.name)}</div>
                                <div class="skill-id">${this.escapeHtml(skill.skill_id)}</div>
                            </div>
                        </div>
                        <div class="skill-description">${this.escapeHtml(skill.description || '无描述')}</div>
                    </div>
                `).join('');
            } else {
                skillsGrid.innerHTML = '<div class="empty-state">暂无可用技能</div>';
            }
        } catch (error) {
            console.error('加载技能失败:', error);
            document.getElementById('skills-grid').innerHTML = 
                '<div class="empty-state">加载失败，请刷新重试</div>';
        }
    }

    async loadTools() {
        try {
            const response = await fetch(`${this.apiBase}/tools`);
            const data = await response.json();
            
            const toolsGrid = document.getElementById('tools-grid');
            if (data.tools && data.tools.length > 0) {
                toolsGrid.innerHTML = data.tools.map(tool => `
                    <div class="tool-card">
                        <div class="tool-card-header">
                            <div class="tool-icon">⚙️</div>
                            <div>
                                <div class="tool-name">${this.escapeHtml(tool.name)}</div>
                                <div class="tool-id">${this.escapeHtml(tool.tool_id)}</div>
                            </div>
                        </div>
                        <div class="tool-description">${this.escapeHtml(tool.description || '无描述')}</div>
                    </div>
                `).join('');
            } else {
                toolsGrid.innerHTML = '<div class="empty-state">暂无可用工具</div>';
            }
        } catch (error) {
            console.error('加载工具失败:', error);
            document.getElementById('tools-grid').innerHTML = 
                '<div class="empty-state">加载失败，请刷新重试</div>';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new JarvisApp();
});
