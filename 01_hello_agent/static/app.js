// CodeMind Assistant - 前端交互逻辑

// ==================== 全局状态 ====================

let currentFilter = 'open';
let websocket = null;

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initChat();
    initWebSocket();
    loadStats();
    
    // 自动加载任务列表
    loadTasks('open');
});

// ==================== 导航切换 ====================

function initNavigation() {
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.section');
    
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            
            // 移除所有 active 类
            navLinks.forEach(l => l.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));
            
            // 添加 active 类到当前链接
            link.classList.add('active');
            
            // 显示对应 section
            const target = link.getAttribute('href').substring(1);
            document.getElementById(target).classList.add('active');
        });
    });
}

// ==================== WebSocket 连接 ====================

function initWebSocket() {
    const clientId = 'user_' + Math.random().toString(36).substr(2, 9);
    const wsUrl = `ws://localhost:8000/ws/${clientId}`;
    
    try {
        websocket = new WebSocket(wsUrl);
        
        websocket.onopen = () => {
            console.log('WebSocket 已连接');
        };
        
        websocket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('收到消息:', data);
            
            if (data.type === 'welcome') {
                showToast(data.message);
            }
        };
        
        websocket.onclose = () => {
            console.log('WebSocket 已断开');
            setTimeout(initWebSocket, 3000); // 3 秒后重连
        };
        
        websocket.onerror = (error) => {
            console.error('WebSocket 错误:', error);
        };
    } catch (error) {
        console.error('WebSocket 连接失败:', error);
    }
}

// ==================== 智能问答 ====================

function initChat() {
    const sendBtn = document.getElementById('sendBtn');
    const chatInput = document.getElementById('chatInput');
    
    sendBtn.addEventListener('click', sendMessage);
    
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

async function sendMessage() {
    const chatInput = document.getElementById('chatInput');
    const question = chatInput.value.trim();
    
    if (!question) return;
    
    // 添加用户消息到聊天界面
    addChatMessage(question, 'user');
    chatInput.value = '';
    
    // 显示加载动画
    const loadingId = addLoadingMessage();
    
    try {
        const useMQE = document.getElementById('useMQE').checked;
        const useHyDE = document.getElementById('useHyDE').checked;
        const useContext = document.getElementById('useContext').checked;
        
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                use_mqe: useMQE,
                use_hyde: useHyDE,
                use_context: useContext
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP 错误：${response.status}`);
        }
        
        const data = await response.json();
        
        // 移除加载动画
        removeLoadingMessage(loadingId);
        
        // 显示助手回答
        addChatMessage(data.answer, 'assistant', data.sources);
        
        // 更新统计
        loadStats();
        
    } catch (error) {
        removeLoadingMessage(loadingId);
        addChatMessage(`❌ 错误：${error.message}`, 'assistant');
    }
}

function addChatMessage(content, type, sources = []) {
    const messagesDiv = document.getElementById('chatMessages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    let sourcesHtml = '';
    if (sources.length > 0) {
        sourcesHtml = `
            <div class="message-sources">
                <strong>来源:</strong>
                <ul>
                    ${sources.map(s => `<li>${s}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    messageDiv.innerHTML = `
        <div class="message-content">
            ${content.replace(/\n/g, '<br>')}
            ${sourcesHtml}
        </div>
    `;
    
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addLoadingMessage() {
    const messagesDiv = document.getElementById('chatMessages');
    const id = 'loading-' + Date.now();
    
    const loadingDiv = document.createElement('div');
    loadingDiv.id = id;
    loadingDiv.className = 'message assistant';
    loadingDiv.innerHTML = `
        <div class="message-content">
            <span class="loading"></span> 思考中...
        </div>
    `;
    
    messagesDiv.appendChild(loadingDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    return id;
}

function removeLoadingMessage(id) {
    const loadingDiv = document.getElementById(id);
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// ==================== 代码库操作 ====================

async function exploreCodebase() {
    const command = document.getElementById('exploreCommand').value.trim();
    if (!command) return;
    
    const resultDiv = document.getElementById('exploreResult');
    resultDiv.innerHTML = '<span class="loading"></span> 执行中...';
    
    try {
        const response = await fetch('/api/codebase/explore', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                command: command,
                save_to_notes: false
            })
        });
        
        const data = await response.json();
        resultDiv.textContent = data.output || '命令执行失败';
        
    } catch (error) {
        resultDiv.textContent = `❌ 错误：${error.message}`;
    }
}

async function analyzeFile() {
    const filePath = document.getElementById('analyzeFile').value.trim();
    if (!filePath) {
        alert('请输入文件路径');
        return;
    }
    
    const resultDiv = document.getElementById('analyzeResult');
    resultDiv.innerHTML = '<span class="loading"></span> 分析中...';
    
    try {
        const response = await fetch(`/api/codebase/analyze?file_path=${encodeURIComponent(filePath)}`, {
            method: 'POST'
        });
        
        const data = await response.json();
        
        let html = `<strong>文件：</strong>${data.file_name || filePath}<br>`;
        if (data.stats) {
            html += `<strong>行数：</strong>${data.stats.lines || 'N/A'}<br>`;
            html += `<strong>大小：</strong>${data.stats.size || 'N/A'} 字节<br>`;
        }
        if (data.preview) {
            html += `<hr><strong>预览：</strong><br><pre>${data.preview}</pre>`;
        }
        
        resultDiv.innerHTML = html;
        
    } catch (error) {
        resultDiv.textContent = `❌ 错误：${error.message}`;
    }
}

async function searchCodebase() {
    const pattern = document.getElementById('searchPattern').value.trim();
    const filePattern = document.getElementById('filePattern').value.trim() || '*.py';
    
    if (!pattern) {
        alert('请输入搜索模式');
        return;
    }
    
    const resultDiv = document.getElementById('searchResult');
    resultDiv.innerHTML = '<span class="loading"></span> 搜索中...';
    
    try {
        const response = await fetch(
            `/api/codebase/search?pattern=${encodeURIComponent(pattern)}&file_pattern=${encodeURIComponent(filePattern)}`,
            { method: 'POST' }
        );
        
        const data = await response.json();
        
        if (data.count === 0) {
            resultDiv.textContent = '未找到匹配结果';
        } else {
            let html = `<strong>找到 ${data.count} 个匹配:</strong><br><br>`;
            if (data.matches) {
                html += `<pre>${data.matches.join('\n')}</pre>`;
            }
            resultDiv.innerHTML = html;
        }
        
    } catch (error) {
        resultDiv.textContent = `❌ 错误：${error.message}`;
    }
}

// ==================== 任务管理 ====================

async function createTask() {
    const title = document.getElementById('taskTitle').value.trim();
    const description = document.getElementById('taskDescription').value.trim();
    const priority = document.getElementById('taskPriority').value;
    
    if (!title) {
        alert('请输入任务标题');
        return;
    }
    
    try {
        const response = await fetch('/api/tasks/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title: title,
                description: description,
                priority: priority,
                tags: ['web']
            })
        });
        
        const data = await response.json();
        
        if (data.task_id) {
            showToast(`✅ 任务已创建：${title}`);
            // 清空输入框
            document.getElementById('taskTitle').value = '';
            document.getElementById('taskDescription').value = '';
            // 刷新任务列表
            loadTasks(currentFilter);
        }
        
    } catch (error) {
        alert(`❌ 创建失败：${error.message}`);
    }
}

async function loadTasks(status = 'open') {
    currentFilter = status;
    
    // 更新过滤器按钮状态
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.classList.remove('active');
        if ((status === 'open' && btn.textContent === '待处理') ||
            (status === 'in_progress' && btn.textContent === '进行中') ||
            (status === 'resolved' && btn.textContent === '已解决') ||
            (!status && btn.textContent === '全部')) {
            btn.classList.add('active');
        }
    });
    
    const taskListDiv = document.getElementById('taskList');
    taskListDiv.innerHTML = '<span class="loading"></span> 加载中...';
    
    try {
        const url = status ? `/api/tasks/list?status=${status}&limit=50` : '/api/tasks/list';
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.tasks.length === 0) {
            taskListDiv.innerHTML = '<p style="text-align:center;color:#999;">暂无任务</p>';
            return;
        }
        
        let html = '';
        data.tasks.forEach(task => {
            html += `
                <div class="task-item priority-${task.priority}">
                    <div style="display:flex;justify-content:space-between;align-items:start;">
                        <div>
                            <strong>${task.title}</strong>
                            ${task.description ? `<p style="margin-top:5px;color:#666;">${task.description}</p>` : ''}
                            <div style="margin-top:8px;font-size:0.85rem;color:#999;">
                                <span>ID: ${task.id}</span> | 
                                <span>优先级：${task.priority}</span> | 
                                <span>状态：${task.status}</span>
                                ${task.tags && task.tags.length > 0 ? `| <span>标签：${task.tags.join(', ')}</span>` : ''}
                            </div>
                        </div>
                        <button onclick="updateTaskStatus('${task.id}', 'resolved')" 
                                class="btn btn-secondary" style="padding:0.4rem 0.8rem;font-size:0.85rem;">
                            ✓ 完成
                        </button>
                    </div>
                </div>
            `;
        });
        
        taskListDiv.innerHTML = html;
        
    } catch (error) {
        taskListDiv.innerHTML = `❌ 加载失败：${error.message}`;
    }
}

async function updateTaskStatus(taskId, newStatus) {
    try {
        const response = await fetch(`/api/tasks/${taskId}/update`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                status: newStatus,
                comment: '通过 Web 界面更新'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('✅ 任务状态已更新');
            loadTasks(currentFilter);
        }
        
    } catch (error) {
        alert(`❌ 更新失败：${error.message}`);
    }
}

// ==================== MCP 服务 ====================

async function connectMCP() {
    const serverType = document.getElementById('mcpServerType').value;
    const customCommand = document.getElementById('mcpCommand').value.trim();
    
    const statusDiv = document.getElementById('mcpStatus');
    statusDiv.innerHTML = '<span class="loading"></span> 连接中...';
    
    try {
        let command = null;
        let args = null;
        
        if (customCommand) {
            const parts = customCommand.split(' ');
            command = parts[0];
            args = parts.slice(1);
        }
        
        const response = await fetch('/api/mcp/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                server_name: serverType,
                command: command,
                args: args
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            statusDiv.innerHTML = `✅ ${data.message} - 服务器：${serverType}`;
            // 刷新 MCP 状态
            loadMCPStatus();
        } else {
            statusDiv.innerHTML = `❌ ${data.message}`;
        }
        
    } catch (error) {
        statusDiv.innerHTML = `❌ 连接失败：${error.message}`;
    }
}

async function callMCPTool() {
    const serverName = document.getElementById('mcpServerName').value.trim();
    const toolName = document.getElementById('mcpToolName').value.trim();
    const argsText = document.getElementById('mcpArguments').value.trim();
    
    if (!serverName || !toolName) {
        alert('请输入服务器名称和工具名称');
        return;
    }
    
    let arguments = {};
    if (argsText) {
        try {
            arguments = JSON.parse(argsText);
        } catch (e) {
            alert('参数必须是有效的 JSON 格式');
            return;
        }
    }
    
    const resultDiv = document.getElementById('mcpToolResult');
    resultDiv.innerHTML = '<span class="loading"></span> 调用中...';
    
    try {
        const response = await fetch('/api/mcp/call_tool', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                server_name: serverName,
                tool_name: toolName,
                arguments: arguments
            })
        });
        
        const data = await response.json();
        
        if (typeof data.result === 'object') {
            resultDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        } else {
            resultDiv.textContent = data.result || '工具调用完成';
        }
        
    } catch (error) {
        resultDiv.textContent = `❌ 调用失败：${error.message}`;
    }
}

async function loadMCPStatus() {
    try {
        const response = await fetch('/api/mcp/status');
        const data = await response.json();
        
        const statusDiv = document.getElementById('mcpStatus');
        if (data.connected_servers > 0) {
            statusDiv.innerHTML = `🟢 已连接 ${data.connected_servers} 个 MCP 服务器`;
        } else {
            statusDiv.innerHTML = '⚪ 未连接任何 MCP 服务器';
        }
        
        // 更新统计
        document.getElementById('statMCP').textContent = data.connected_servers;
        
    } catch (error) {
        console.error('加载 MCP 状态失败:', error);
    }
}

// ==================== 统计信息 ====================

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        document.getElementById('statDocuments').textContent = data.documents_loaded || 0;
        document.getElementById('statChunks').textContent = data.chunks_created || 0;
        document.getElementById('statQuestions').textContent = data.questions_asked || 0;
        document.getElementById('statTasks').textContent = data.notes_created || 0;
        document.getElementById('statCommands').textContent = data.commands_executed || 0;
        
        // 加载 MCP 状态
        loadMCPStatus();
        
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

function refreshStats() {
    loadStats();
    showToast('🔄 统计已刷新');
}

async function generateReport() {
    const resultDiv = document.getElementById('reportResult');
    resultDiv.innerHTML = '<span class="loading"></span> 生成中...';
    
    try {
        const response = await fetch('/api/report');
        const data = await response.json();
        
        let html = `<strong>✅ 报告已生成</strong><br><br>`;
        html += `<strong>统计摘要:</strong><br>`;
        if (data.statistics) {
            html += `<pre>${JSON.stringify(data.statistics, null, 2)}</pre>`;
        }
        html += `<br><strong>导出文件:</strong><br>`;
        html += `📄 ${data.report_path}<br>`;
        html += `📝 ${data.notes_path}`;
        
        resultDiv.innerHTML = html;
        
    } catch (error) {
        resultDiv.textContent = `❌ 生成失败：${error.message}`;
    }
}

// ==================== 工具函数 ====================

function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--success-color);
        color: white;
        padding: 1rem 2rem;
        border-radius: 8px;
        box-shadow: var(--shadow-lg);
        z-index: 1000;
        animation: slideInRight 0.3s ease-out;
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 添加动画样式
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
    }
`;
document.head.appendChild(style);
