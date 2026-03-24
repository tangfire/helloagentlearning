# API 接口文档

本文档详细介绍 CodeMind 提供的所有 REST API 接口。

## 基础信息

**Base URL**: `http://localhost:8000`

**认证方式**: 当前版本使用默认用户（后续版本将添加 JWT 认证）

**响应格式**: JSON

## 工作空间管理 API

### 1. 创建工作空间

**端点**: `POST /api/workspace/create`

**请求体**:
```json
{
  "name": "我的项目",
  "description": "项目描述（可选）"
}
```

**响应**:
```json
{
  "success": true,
  "workspace_id": "db50d0e6",
  "name": "我的项目",
  "message": "工作空间 '我的项目' 已创建"
}
```

**说明**: 
- 返回的 `workspace_id` 是短 ID（8 位）
- 系统会自动切换到新创建的工作空间

### 2. 获取工作空间列表

**端点**: `GET /api/workspace/list`

**响应**:
```json
{
  "workspaces": [
    {
      "id": "db50d0e6",
      "name": "我的项目",
      "description": "项目描述",
      "path": "C:\\Users\\...\\workspaces\\db50d0e6",
      "created_at": "2024-03-24T10:30:00",
      "document_count": 5,
      "session_count": 2
    }
  ],
  "current_workspace_id": "db50d0e6",
  "count": 1
}
```

### 3. 切换工作空间

**端点**: `POST /api/workspace/switch`

**请求体**:
```json
{
  "workspace_id": "db50d0e6"
}
```

**响应**:
```json
{
  "success": true,
  "workspace": {
    "id": "db50d0e6",
    "name": "我的项目",
    ...
  },
  "message": "已切换到工作空间 '我的项目'"
}
```

**说明**: 支持短 ID 和完整 UUID 两种方式

### 4. 删除工作空间

**端点**: `DELETE /api/workspace/delete/{workspace_id}`

**响应**:
```json
{
  "success": true,
  "message": "工作空间已删除"
}
```

**注意**: 删除工作空间会级联删除所有关联的文档和笔记

## 文件上传 API

### 5. 上传文件

**端点**: `POST /api/upload`

**请求格式**: `multipart/form-data`

**参数**:
- `files`: 文件列表（支持多文件上传）

**示例** (使用 curl):
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "files=@document1.pdf" \
  -F "files=@document2.py"
```

**响应**:
```json
{
  "success": true,
  "files": [
    {
      "original_filename": "document1.pdf",
      "saved_filename": "document1_20240324_143000.pdf",
      "size": 102400,
      "content_type": "application/pdf",
      "path": "C:\\...\\documents\\document1_20240324_143000.pdf"
    }
  ],
  "count": 2,
  "workspace_id": "db50d0e6"
}
```

**处理流程**:
1. 保存文件到文件系统
2. 使用 MarkItDown 转换为 Markdown
3. 文本分块（1000 tokens/chunk）
4. 生成向量嵌入（OpenAI embeddings）
5. 保存到 PostgreSQL（元数据）
6. 保存到 Milvus（向量数据）
7. 更新文档状态：processing → indexed

**错误响应**:
```json
{
  "detail": "部分文件索引失败:\ndocument1.pdf: 连接超时"
}
```

### 6. 获取文档列表

**端点**: `GET /api/documents`

**查询参数**:
- `workspace_id`: 工作空间 ID（可选，默认当前工作空间）

**响应**:
```json
{
  "documents": [
    {
      "id": "005932fc-195b-45ea-9617-be55c779dd03",
      "workspace_id": "91802ebc-...",
      "filename": "document1.pdf",
      "original_filename": "document1.pdf",
      "file_size": 102400,
      "mime_type": "application/pdf",
      "uploader_id": "00000000-...",
      "uploaded_at": "2024-03-24T14:30:00",
      "status": "indexed",
      "tags": ["重要", "技术文档"],
      "version": 1
    }
  ],
  "count": 1
}
```

### 7. 删除文档

**端点**: `DELETE /api/documents/{document_id}`

**响应**:
```json
{
  "success": true,
  "message": "文档已删除"
}
```

**说明**: 级联删除 PostgreSQL 中的分块记录和 Milvus 中的向量

## 智能问答 API

### 8. 发送问题

**端点**: `POST /api/chat`

**请求体**:
```json
{
  "question": "项目的架构是什么？",
  "use_mqe": true,      // 是否使用多查询扩展（可选，默认 true）
  "use_hyde": true,     // 是否使用假设文档嵌入（可选，默认 true）
  "use_context": true   // 是否使用历史上下文（可选，默认 true）
}
```

**响应**:
```json
{
  "answer": "项目采用 RAG 架构，结合了 LangChain 和 Milvus 向量数据库...",
  "sources": [
    {
      "filename": "architecture.md",
      "chunk_index": 0,
      "score": 0.92
    },
    {
      "filename": "README.md",
      "chunk_index": 2,
      "score": 0.85
    }
  ],
  "confidence": 0.88,
  "retrieval_method": "hybrid",
  "context_used": true,
  "workspace_id": "db50d0e6",
  "workspace_info": "当前工作空间包含以下 5 个文档：\n  - 📄 architecture.md (15.2 KB, 状态：indexed)"
}
```

**回答质量指标**:
- `confidence`: 置信度（0-1）
- `sources`: 来源文档及相似度分数
- `context_used`: 是否使用了上下文

## 会话管理 API

### 9. 保存会话

**端点**: `POST /api/session/save`

**请求体**:
```json
{
  "workspace_id": "db50d0e6",
  "session_name": "第一次讨论"
}
```

**响应**:
```json
{
  "success": true,
  "session_id": "abc12345",
  "message": "会话 '第一次讨论' 已保存"
}
```

**说明**: 需要前端传递实际的对话历史消息数组

### 10. 获取会话列表

**端点**: `GET /api/session/list?workspace_id=db50d0e6`

**响应**:
```json
{
  "sessions": [
    {
      "id": "abc12345",
      "name": "第一次讨论",
      "workspace_id": "db50d0e6",
      "messages": [...],
      "created_at": "2024-03-24T15:00:00"
    }
  ],
  "count": 1
}
```

### 11. 加载会话

**端点**: `GET /api/session/load/{session_id}`

**响应**:
```json
{
  "session_id": "abc12345",
  "messages": [
    {
      "role": "user",
      "content": "什么是 RAG？"
    },
    {
      "role": "assistant",
      "content": "RAG 是检索增强生成..."
    }
  ]
}
```

## 笔记管理 API

### 12. 创建笔记/任务

**端点**: `POST /api/notes`

**请求体**:
```json
{
  "title": "实现用户认证功能",
  "content": "需要添加 JWT 认证和 OAuth2 支持",
  "note_type": "task",      // note, task, decision, question
  "priority": "high",       // low, medium, high
  "tags": ["功能", "紧急"]
}
```

**响应**:
```json
{
  "success": true,
  "note_id": "note-uuid-here",
  "message": "任务已创建"
}
```

### 13. 更新笔记状态

**端点**: `PATCH /api/notes/{note_id}`

**请求体**:
```json
{
  "status": "completed",    // open, completed, archived
  "comment": "已完成，测试通过"
}
```

### 14. 获取笔记列表

**端点**: `GET /api/notes?workspace_id=db50d0e6&type=task&status=open`

**查询参数**:
- `workspace_id`: 工作空间 ID
- `type`: 笔记类型（可选）
- `status`: 状态（可选）

**响应**:
```json
{
  "notes": [
    {
      "id": "note-uuid",
      "title": "实现用户认证功能",
      "note_type": "task",
      "status": "open",
      "priority": "high",
      "created_at": "2024-03-24T10:00:00"
    }
  ],
  "count": 1
}
```

## MCP (Model Context Protocol) API

### 15. 连接 MCP 服务器

**端点**: `POST /api/mcp/connect`

**请求体**:
```json
{
  "server_name": "filesystem",
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-filesystem"]
}
```

**响应**:
```json
{
  "success": true,
  "message": "MCP 服务器已连接"
}
```

### 16. 调用 MCP 工具

**端点**: `POST /api/mcp/call`

**请求体**:
```json
{
  "server_name": "filesystem",
  "tool_name": "read_file",
  "arguments": {
    "path": "/path/to/file.txt"
  }
}
```

**响应**:
```json
{
  "success": true,
  "result": {
    "content": "文件内容..."
  }
}
```

### 17. 列出 MCP 工具

**端点**: `GET /api/mcp/tools/{server_name}`

**响应**:
```json
{
  "tools": [
    {
      "name": "read_file",
      "description": "读取文件内容",
      "parameters": {...}
    }
  ]
}
```

## 系统管理 API

### 18. 健康检查

**端点**: `GET /api/health`

**响应**:
```json
{
  "status": "healthy",
  "timestamp": "2024-03-24T16:00:00",
  "assistant_initialized": true,
  "workspace_count": 3,
  "current_workspace": "我的项目"
}
```

### 19. 获取统计信息

**端点**: `GET /api/stats`

**响应**:
```json
{
  "total_documents": 15,
  "total_chunks": 150,
  "milvus_collection_count": 150,
  "workspace_stats": {
    "db50d0e6": {
      "documents": 5,
      "chunks": 50
    }
  }
}
```

## 错误处理

### 标准错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

### 常见错误码

| HTTP 状态码 | 含义 | 示例 |
|-----------|------|------|
| 400 | 请求参数错误 | "没有活跃的工作空间" |
| 404 | 资源不存在 | "工作空间不存在" |
| 500 | 服务器内部错误 | "数据库连接失败" |

### 错误处理最佳实践

```python
from fastapi import HTTPException

@app.post("/api/upload")
async def upload_files(files: List[UploadFile]):
    try:
        current_ws = workspace_manager.get_current_workspace()
        if not current_ws:
            raise HTTPException(
                status_code=400, 
                detail="没有活跃的工作空间"
            )
        
        # 处理逻辑...
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## WebSocket 实时通信

### 连接 WebSocket

**端点**: `WS /ws`

**连接**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
```

**接收消息**:
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('收到消息:', data);
};
```

**发送消息**:
```javascript
ws.send(JSON.stringify({
  type: 'chat',
  question: '你好'
}));
```

**消息格式**:
```json
{
  "type": "chat_response",
  "answer": "你好！有什么可以帮助你的？",
  "sources": [],
  "status": "streaming"  // streaming, complete, error
}
```

## 使用示例

### Python 示例

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. 创建工作空间
response = requests.post(f"{BASE_URL}/api/workspace/create", json={
    "name": "测试项目",
    "description": "用于测试"
})
workspace_id = response.json()["workspace_id"]

# 2. 上传文件
with open("document.pdf", "rb") as f:
    files = {"files": f}
    response = requests.post(f"{BASE_URL}/api/upload", files=files)

# 3. 发送问题
response = requests.post(f"{BASE_URL}/api/chat", json={
    "question": "文档的主要内容是什么？"
})
answer = response.json()["answer"]
print(answer)
```

### JavaScript 示例

```javascript
const BASE_URL = 'http://localhost:8000';

// 1. 创建工作空间
async function createWorkspace(name, description) {
  const response = await fetch(`${BASE_URL}/api/workspace/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description })
  });
  return await response.json();
}

// 2. 上传文件
async function uploadFile(file) {
  const formData = new FormData();
  formData.append('files', file);
  
  const response = await fetch(`${BASE_URL}/api/upload`, {
    method: 'POST',
    body: formData
  });
  return await response.json();
}

// 3. 发送问题
async function askQuestion(question) {
  const response = await fetch(`${BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question })
  });
  return await response.json();
}
```

## 性能优化建议

### 1. 批量上传文件

```python
# 推荐：一次上传多个文件
files = [
    ('files', open('doc1.pdf', 'rb')),
    ('files', open('doc2.py', 'rb')),
    ('files', open('doc3.md', 'rb'))
]
response = requests.post(url, files=files)
```

### 2. 流式响应

对于长回答，使用 WebSocket 流式传输：

```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.status === 'streaming') {
    // 逐字显示回答
    displayToken(data.token);
  }
};
```

### 3. 缓存常用查询结果

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_answer(question_hash: str):
    # 从缓存获取
    pass
```

## 版本历史

### v2.0 (当前版本)
- ✅ 新增数据库增强版 API
- ✅ 支持工作空间短 ID 和 UUID
- ✅ 改进文件上传流程
- ✅ 添加 MCP 集成

### v1.0
- ✅ 基础 RAG 问答 API
- ✅ FAISS 向量存储
- ✅ 简单工作空间管理
