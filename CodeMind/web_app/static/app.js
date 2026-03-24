// CodeMind Assistant - 前端交互逻辑

// ==================== 全局状态 ====================

let currentFilter = 'open';
let websocket = null;
let currentWorkspaceId = null;

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 DOM 已加载，开始初始化...');
    
    initChat();
    initWebSocket();
    loadWorkspaces();
    
    // 立即加载文档列表（不延迟）
    loadWorkspaceDocuments();
    
    console.log('✅ 初始化完成');
});

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
        
        // 显示助手回答（包含工作空间信息）
        addChatMessage(data.answer, 'assistant', data.sources, data.workspace_info);
        
    } catch (error) {
        removeLoadingMessage(loadingId);
        addChatMessage(`❌ 错误：${error.message}`, 'assistant');
    }
}

function addChatMessage(content, type, sources = [], workspaceInfo = null) {
    const messagesDiv = document.getElementById('chatMessages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    // 工作空间信息展示（仅针对助手消息）
    let workspaceHtml = '';
    if (workspaceInfo && type === 'assistant') {
        workspaceHtml = `
            <div class="workspace-info" style="margin-bottom:10px;padding:8px;background:#f5f5f5;border-left:3px solid #4CAF50;border-radius:4px;font-size:0.85rem;">
                <strong>📁 当前工作空间文档：</strong><br>
                <div style="margin-top:5px;max-height:150px;overflow-y:auto;">${workspaceInfo.replace(/\n/g, '<br>')}</div>
            </div>
        `;
    }
    
    // 已移除来源显示
    
    messageDiv.innerHTML = `
        <div class="message-content">
            ${workspaceHtml}
            ${content.replace(/\n/g, '<br>')}
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

// ==================== 工作空间管理 ====================

// 切换工作空间面板显示
function toggleWorkspacePanel() {
    const panel = document.getElementById('workspacePanel');
    panel.classList.toggle('show');
}

// 加载工作空间列表
async function loadWorkspaces() {
    try {
        const wsResponse = await fetch('/api/workspace/list');
        const wsData = await wsResponse.json();
        
        // 更新当前工作空间显示
        const currentWsName = document.getElementById('currentWorkspaceName');
        if (wsData.current_workspace_id) {
            const currentWs = wsData.workspaces.find(ws => ws.id === wsData.current_workspace_id);
            if (currentWs) {
                currentWsName.textContent = currentWs.name;
            }
        } else {
            currentWsName.textContent = '未选择';
        }
        
        const workspaceList = document.getElementById('workspaceList');
        
        if (wsData.workspaces.length === 0) {
            workspaceList.innerHTML = '<p style="text-align:center;color:#999;">暂无工作空间，创建一个吧！</p>';
        } else {
            let html = '';
            wsData.workspaces.forEach(ws => {
                const isActive = ws.id === wsData.current_workspace_id;
                
                html += `
                    <div class="workspace-item ${isActive ? 'active' : ''}" data-id="${ws.id}">
                        <div>
                            <strong>${ws.name}</strong>
                            ${ws.description ? `<p style="font-size:0.85rem;color:#666;">${ws.description}</p>` : ''}
                        </div>
                        <div style="display:flex;gap:0.5rem;">
                            ${!isActive ? `<button onclick="switchWorkspace('${ws.id}')" class="btn btn-sm btn-secondary">切换</button>` : ''}
                            <button onclick="deleteWorkspace('${ws.id}')" class="btn btn-sm btn-danger">删除</button>
                        </div>
                    </div>
                `;
            });
            workspaceList.innerHTML = html;
        }
        
    } catch (error) {
        console.error('加载工作空间失败:', error);
        showToast(`❌ 加载失败：${error.message}`);
    }
}

async function createWorkspace() {
    const name = document.getElementById('workspaceName').value.trim();
    const description = document.getElementById('workspaceDesc').value.trim();
    
    if (!name) {
        alert('请输入工作空间名称');
        return;
    }
    
    try {
        const response = await fetch('/api/workspace/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: name,
                description: description
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`✅ ${data.message}`);
            document.getElementById('workspaceName').value = '';
            document.getElementById('workspaceDesc').value = '';
            loadWorkspaces();
        }
        
    } catch (error) {
        alert(`❌ 创建失败：${error.message}`);
    }
}

// 暴露全局函数供 HTML onclick 使用
window.createWorkspace = createWorkspace;
window.toggleWorkspacePanel = toggleWorkspacePanel;
window.handleDrop = handleDrop;
window.handleDragOver = handleDragOver;
window.handleDragLeave = handleDragLeave;
window.handleFileSelect = handleFileSelect;
window.switchWorkspace = switchWorkspace;
window.deleteWorkspace = deleteWorkspace;

async function switchWorkspace(workspaceId) {
    try {
        const response = await fetch('/api/workspace/switch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                workspace_id: workspaceId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`🔄 ${data.message}`);
            loadWorkspaces();
            // 刷新文档列表
            loadWorkspaceDocuments();
        }
        
    } catch (error) {
        alert(`❌ 切换失败：${error.message}`);
    }
}

async function deleteWorkspace(workspaceId) {
    if (!confirm('确定要删除这个工作空间吗？此操作不可恢复！')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/workspace/delete/${workspaceId}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast(`✅ ${data.message}`);
            loadWorkspaces();
            // 刷新文档列表
            loadWorkspaceDocuments();
        }
        
    } catch (error) {
        alert(`❌ 删除失败：${error.message}`);
    }
}

// ==================== 文件上传 ====================

function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.add('drag-over');
}

function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('drag-over');
}

async function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('drag-over');
    
    const files = event.dataTransfer.files;
    await uploadFiles(files);
}

function handleFileSelect(event) {
    const files = event.target.files;
    uploadFiles(files);
}

async function uploadFiles(files) {
    if (files.length === 0) return;
    
    // 先检查是否有活跃的工作空间
    try {
        const wsResponse = await fetch('/api/workspace/list');
        const wsData = await wsResponse.json();
        
        if (!wsData.current_workspace_id) {
            alert('⚠️ 请先创建或选择一个工作空间，然后再上传文件！');
            return;
        }
    } catch (error) {
        alert(`❌ 检查工作空间失败：${error.message}`);
        return;
    }
    
    const dropZone = document.getElementById('dropZone');
    // 显示上传中状态
    const originalContent = dropZone.innerHTML;
    dropZone.innerHTML = '<span class="loading"></span> 上传中...';
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: '未知错误' }));
            throw new Error(`${response.status}: ${errorData.detail || '上传失败'}`);
        }
        
        const data = await response.json();
        
        // 恢复拖拽区域内容
        dropZone.innerHTML = originalContent;
        
        if (data.success) {
            // 显示上传记录
            const statusDiv = document.getElementById('uploadStatus');
            let html = '<ul style="list-style:none;padding:0;margin-top:0.5rem;">';
            data.files.forEach(file => {
                html += `
                    <li style="padding:0.5rem;margin:0.25rem 0;background:#f8f9fa;border-radius:4px;border-left:3px solid #28a745;font-size:0.85rem;">
                        <strong>✅ ${file.original_filename}</strong>
                        <span style="font-size:0.75rem;color:#666;"> (${(file.size / 1024).toFixed(2)} KB)</span>
                        ${file.original_filename !== file.saved_filename ? `<br><span style="font-size:0.7rem;color:#999;">→ ${file.saved_filename}</span>` : ''}
                    </li>
                `;
            });
            html += '</ul>';
            statusDiv.innerHTML = html;
            
            showToast(`✅ 成功上传 ${data.count} 个文件`);
            
            // 清空文件选择
            document.getElementById('fileInput').value = '';
            
            // 刷新文档列表
            loadWorkspaceDocuments();
        }
        
    } catch (error) {
        // 恢复拖拽区域内容
        dropZone.innerHTML = originalContent;
        alert(`❌ 上传失败：${error.message}`);
    }
}

// 加载当前工作空间的文档列表
async function loadWorkspaceDocuments() {
    console.log('📂 开始加载文档列表...');
    const fileListDiv = document.getElementById('workspaceDocuments');
    if (!fileListDiv) {
        console.error('❌ 找不到 workspaceDocuments 元素');
        return;
    }
    
    try {
        console.log('📡 请求工作空间列表...');
        const wsResponse = await fetch('/api/workspace/list');
        const wsData = await wsResponse.json();
        console.log('📦 收到工作空间数据:', wsData);
        
        // 如果没有工作空间，显示提示
        if (!wsData.current_workspace_id) {
            console.log('⚠️ 没有活跃工作空间');
            fileListDiv.innerHTML = '<p style="text-align:center;color:#999;font-size:0.85rem;">请先创建工作空间</p>';
            return;
        }
        
        const currentWs = wsData.workspaces.find(ws => ws.id === wsData.current_workspace_id);
        if (!currentWs) {
            console.log('⚠️ 未找到当前工作空间');
            fileListDiv.innerHTML = '<p style="text-align:center;color:#999;">未找到工作空间</p>';
            return;
        }
        
        console.log('📂 当前工作空间:', currentWs.name, '路径:', currentWs.path);
        
        // 使用新的文档列表 API
        console.log('🔍 获取文档列表...');
        const docsResponse = await fetch('/api/documents/list');
        const docsData = await docsResponse.json();
        console.log('📦 收到文档数据:', docsData);
        
        if (docsData.documents && docsData.documents.length > 0) {
            let html = '<ul style="list-style:none;padding:0;">';
            
            docsData.documents.forEach(doc => {
                // 只显示支持的文件类型
                if (/\.(pdf|txt|md|doc|docx|xls|xlsx|ppt|pptx|py|js|ts|java|cpp|c|h|json|yaml|yml|xml|html|css|sql|sh|bat)$/i.test(doc.filename)) {
                    const fileSizeKB = (doc.size / 1024).toFixed(2);
                    html += `<li style="padding:0.5rem;background:#f8f9fa;margin:0.25rem 0;border-radius:4px;border-left:3px solid #007bff;display:flex;justify-content:space-between;align-items:center;">
                        <div style="flex:1;">
                            <span style="font-weight:500;">📄 ${doc.filename}</span>
                            <span style="font-size:0.75rem;color:#999;margin-left:0.5rem;">(${fileSizeKB} KB)</span>
                        </div>
                        <span style="font-size:0.75rem;color:#999;">${new Date(doc.modified_at).toLocaleString('zh-CN')}</span>
                    </li>`;
                }
            });
            
            html += '</ul>';
            fileListDiv.innerHTML = html;
            console.log('✅ 文档列表加载完成，共', docsData.documents.length, '个文件');
        } else {
            fileListDiv.innerHTML = '<p style="text-align:center;color:#999;font-size:0.85rem;">暂无文件</p>';
            console.log('ℹ️ 目录为空');
        }
    } catch (error) {
        console.error('❌ 加载文档列表失败:', error);
        fileListDiv.innerHTML = '<p style="text-align:center;color:#dc3545;font-size:0.85rem;">加载失败，请刷新页面</p>';
    }
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
