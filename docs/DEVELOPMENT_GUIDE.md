# CodeMind 开发指南

本文档面向开发者，介绍项目的开发环境配置、代码结构和扩展指南。

## 开发环境配置

### 1. Python 环境

```bash
# 创建虚拟环境（可选）
python -m venv venv
.\venv\Scripts\Activate  # Windows
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库环境

#### 方案 A: Docker Compose (推荐)
```bash
cd CodeMind
docker-compose up -d postgres milvus etcd minio
```

#### 方案 B: 本地安装
- PostgreSQL 15+ with pgvector
- Milvus 2.x

### 3. 环境变量配置

编辑 `01_hello_agent/.env`:

```env
# LLM 配置
OPENAI_API_KEY=sk-xxx
MODEL=gpt-4o-mini
BASE_URL=https://api.openai-proxy.org/v1

# 数据库配置
POSTGRES_USER=codemind
POSTGRES_PASSWORD=codemind2024
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=codemind

# Milvus 配置
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

## 代码结构详解

### 核心模块

#### 1. `core/` - 核心业务逻辑

```
core/
├── codemind_assistant.py       # 基础助手（FAISS 版本）
├── codemind_assistant_db.py    # 数据库增强版助手 ⭐
├── context_builder.py          # 上下文构建器
├── memory_system.py            # 记忆管理系统
└── note_tool.py                # 笔记工具
```

**关键类**:
- `CodeMindAssistantDB`: 主要助手类，整合所有功能
- `ContextBuilder`: 构建问答上下文
- `MemorySystem`: 管理短期和长期记忆

#### 2. `database/` - 数据访问层

```
database/
├── models.py           # SQLAlchemy ORM 模型
├── dao.py              # 数据访问对象（DAO）
├── db_connection.py    # 数据库连接管理
└── milvus_client.py    # Milvus 向量数据库客户端
```

**数据库模型**:
- `User`: 用户表
- `Workspace`: 工作空间表
- `Document`: 文档表
- `DocumentChunk`: 文档分块表
- `Note`: 笔记表（任务、决策、问题）
- `OperationLog`: 操作日志表
- `ConversationHistory`: 会话历史表

#### 3. `web_app/` - Web 应用

```
web_app/
├── web_api.py          # FastAPI 路由和 API
└── static/
    ├── index.html      # 前端页面
    ├── app.js          # 前端逻辑
    └── style.css       # 样式文件
```

**主要 API 端点**:
- `POST /api/workspace/create` - 创建工作空间
- `POST /api/upload` - 上传文件
- `POST /api/chat` - 智能问答
- `GET /api/documents` - 获取文档列表

#### 4. `tools/` - 工具集

```
tools/
├── mcp_server.py           # MCP 服务器
├── mcp_client.py           # MCP 客户端
├── pdf_assistant.py        # PDF 处理工具
├── advanced_pdf_assistant.py  # 高级 PDF 处理
├── terminal_tool.py        # 终端命令执行
└── system_summary.py       # 系统摘要工具
```

## 核心流程解析

### 1. 工作空间创建流程

```python
# 1. 文件系统层面创建目录
workspace_id = workspace_manager.create_workspace(name, description)
# 返回：短 ID (8 位), 如 "db50d0e6"

# 2. 切换到该工作空间
workspace_manager.switch_workspace(workspace_id)

# 3. 初始化助手时同步到数据库
assistant = get_assistant_db()
# 自动在数据库中创建工作空间记录
# 返回：完整 UUID (36 位), 如 "91802ebc-9dcd-4e53-a037-74f7347ffb0b"
```

**关键点**:
- 短 ID 用于文件系统路径
- 完整 UUID 用于数据库外键关联
- 系统自动同步两种 ID

### 2. 文件上传与索引流程

```python
# 1. 接收上传文件
@app.post("/api/upload")
async def upload_files(files: List[UploadFile]):
    # 保存到文件系统
    file_path = save_file(file)
    
    # 2. 调用助手处理
    assistant.upload_document(file_path, filename)
    
    # 3. 文档处理流程
    # a. 使用 MarkItDown 转换为 Markdown
    markdown = markitdown.convert(file_path)
    
    # b. 文本分块
    chunks = text_splitter.split_text(markdown)
    
    # c. 生成向量嵌入
    embeddings = embeddings.embed_documents(chunks)
    
    # d. 保存到 PostgreSQL (元数据)
    doc = doc_dao.create_document(...)
    
    # e. 保存到 Milvus (向量)
    doc_dao.add_chunks(doc.id, chunks, embeddings)
```

### 3. 智能问答流程

```python
def ask(self, question: str, use_context: bool = True):
    # 1. 生成查询向量
    query_vector = self.embeddings.embed_query(question)
    
    # 2. 混合检索
    results = retriever.hybrid_search(
        query_vector=query_vector,
        workspace_id=self.workspace_id,
        k=5,
        filters=None
    )
    
    # 3. 构建上下文
    context_text = build_context(results)
    
    # 4. 构建 Prompt
    prompt = build_prompt(
        question=question,
        context=context_text,
        workspace_info=workspace_docs
    )
    
    # 5. 调用 LLM
    response = self.llm.invoke(prompt)
    
    # 6. 保存会话历史
    conv_dao.save_conversation(...)
    
    return {
        'answer': response.content,
        'sources': results,
        'context_used': True
    }
```

## 扩展指南

### 添加新的文档格式支持

MarkItDown 已支持大多数格式，如需自定义处理：

```python
# 在 codemind_assistant_db.py 中添加
def process_custom_format(self, file_path: str):
    if file_path.endswith('.custom'):
        # 自定义处理逻辑
        content = self.custom_parser(file_path)
        return content
```

### 添加新的 MCP 工具

```python
# tools/my_custom_tool.py
from mcp.server import Server

class MyCustomTool:
    def __init__(self):
        self.name = "my_tool"
    
    async def execute(self, **kwargs):
        # 实现工具逻辑
        result = do_something(**kwargs)
        return result
```

### 自定义检索策略

```python
# 在 RetrieverService 中添加
def custom_search(self, query: str, custom_param: str):
    # 自定义检索逻辑
    results = self.milvus.custom_query(...)
    return results
```

## 测试指南

### 单元测试

```python
# tests/test_context_engineering.py
import unittest

class TestContextEngineering(unittest.TestCase):
    def test_build_context(self):
        # 测试上下文构建
        context = build_context(docs)
        self.assertIsNotNone(context)
```

### API 测试

```bash
# 测试工作空间创建
curl -X POST http://localhost:8000/api/workspace/create \
  -H "Content-Type: application/json" \
  -d '{"name":"测试","description":"测试描述"}'

# 测试文件上传
curl -X POST http://localhost:8000/api/upload \
  -F "files=@test.txt"

# 测试问答
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"项目结构是什么？"}'
```

## 性能优化建议

### 1. 向量检索优化
- 使用 Milvus 的索引加速检索
- 合理设置分块大小（推荐 1000 tokens）
- 使用过滤表达式减少检索范围

### 2. 数据库优化
- 为常用查询字段添加索引
- 使用连接池管理数据库连接
- 定期清理过期数据

### 3. 缓存策略
- 使用 FAISS 作为本地缓存
- 热点工作空间预加载到内存
- LLM 响应缓存（相同问题直接返回）

## 故障排查

### 常见问题诊断

#### 1. 数据库连接失败
```bash
# 检查 PostgreSQL 是否运行
docker ps | grep postgres

# 检查连接配置
cat CodeMind/.env | grep POSTGRES

# 测试连接
psql -h localhost -U codemind -d codemind
```

#### 2. Milvus 连接失败
```bash
# 检查 Milvus 容器
docker ps | grep milvus

# 查看 Milvus 日志
docker logs milvus-standalone
```

#### 3. 文件上传失败
```python
# 检查工作空间是否存在
current_ws = workspace_manager.get_current_workspace()
print(f"当前工作空间：{current_ws}")

# 检查目录权限
import os
os.access(upload_dir, os.W_OK)
```

## 部署指南

### 生产环境部署

1. **使用 Nginx 反向代理**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

2. **使用 Gunicorn 运行 FastAPI**
```bash
pip install gunicorn uvicorn

gunicorn -w 4 -k uvicorn.workers.UvicornWorker \
  web_app.web_api:app \
  --bind 0.0.0.0:8000
```

3. **配置 HTTPS**
```bash
# 使用 Let's Encrypt
certbot --nginx -d your-domain.com
```

## 贡献代码

### 提交流程
1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范
- 遵循 PEP 8 风格指南
- 使用类型注解
- 编写清晰的文档字符串
- 添加单元测试

## 资源链接

- [LangChain 文档](https://python.langchain.com/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Milvus 文档](https://milvus.io/docs)
- [PostgreSQL + pgvector](https://github.com/pgvector/pgvector)
