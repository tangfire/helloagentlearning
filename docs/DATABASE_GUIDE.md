# 数据库架构指南

本文档详细介绍 CodeMind 的数据库架构设计、表结构和最佳实践。

## 架构概述

CodeMind 采用 **双存储引擎** 架构：

```
┌─────────────────────────────────────────────┐
│          PostgreSQL (关系型数据库)           │
│  - 用户信息                                  │
│  - 工作空间元数据                            │
│  - 文档元数据                                │
│  - 笔记和任务                                │
│  - 操作日志                                  │
│  - 会话历史                                  │
└─────────────────────────────────────────────┘
                    ↕ 同步
┌─────────────────────────────────────────────┐
│          Milvus (向量数据库)                 │
│  - 文档分块向量                              │
│  - 相似度检索                                │
│  - 混合查询                                  │
└─────────────────────────────────────────────┘
```

## 数据库表结构

### 1. 用户表 (users)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**用途**: 存储用户账户信息，支持多用户系统。

### 2. 工作空间表 (workspaces)

```sql
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_workspaces_owner ON workspaces(owner_id);
CREATE INDEX idx_workspaces_name ON workspaces(name);
```

**用途**: 
- 每个用户可以有多个工作空间
- 工作空间之间数据隔离
- 外键约束保证数据一致性

### 3. 文档表 (documents) ⭐

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(100),
    uploader_id UUID REFERENCES users(id),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'processing' CHECK (status IN ('processing', 'indexed', 'failed')),
    error_message TEXT,
    tags VARCHAR[],
    metadata JSONB DEFAULT '{}',
    version INTEGER DEFAULT 1
);

CREATE INDEX idx_documents_workspace ON documents(workspace_id);
CREATE INDEX idx_documents_filename ON documents(filename);
CREATE INDEX idx_documents_status ON documents(status);
```

**关键字段**:
- `workspace_id`: 外键关联到 workspaces 表
- `status`: 文档处理状态（processing → indexed / failed）
- `metadata`: JSONB 类型存储灵活元数据

### 4. 文档分块表 (document_chunks) ⭐

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding TEXT,  -- 临时存储，实际向量在 Milvus
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE (document_id, chunk_index)
);

CREATE INDEX idx_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_chunks_metadata ON document_chunks USING GIN (metadata);
```

**用途**:
- 存储文档分块的文本内容
- 与 Milvus 向量一一对应
- 通过 `document_id` 级联删除

### 5. 笔记表 (notes)

```sql
CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    content TEXT,
    note_type VARCHAR(20) DEFAULT 'note' CHECK (note_type IN ('note', 'task', 'decision', 'question')),
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'completed', 'archived')),
    priority VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    tags VARCHAR[],
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notes_workspace ON notes(workspace_id);
CREATE INDEX idx_notes_user ON notes(user_id);
CREATE INDEX idx_notes_type ON notes(note_type);
CREATE INDEX idx_notes_status ON notes(status);
```

**用途**: 任务管理、决策记录、问题跟踪。

### 6. 操作日志表 (operation_logs)

```sql
CREATE TABLE operation_logs (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    workspace_id UUID REFERENCES workspaces(id),
    action VARCHAR(50) NOT NULL CHECK (action IN (
        'UPLOAD_DOCUMENT', 'DELETE_DOCUMENT', 'ASK_QUESTION', 
        'CREATE_NOTE', 'EXECUTE_COMMAND', 'SWITCH_WORKSPACE'
    )),
    target_type VARCHAR(50),
    target_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_logs_user ON operation_logs(user_id);
CREATE INDEX idx_logs_workspace ON operation_logs(workspace_id);
CREATE INDEX idx_logs_action ON operation_logs(action);
CREATE INDEX idx_logs_created ON operation_logs(created_at);
```

**用途**: 审计和安全追踪。

### 7. 会话历史表 (conversation_history)

```sql
CREATE TABLE conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    workspace_id UUID REFERENCES workspaces(id),
    session_id VARCHAR(100) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    context_used JSONB DEFAULT '[]',
    retrieval_strategy JSONB,
    quality_score VARCHAR(3),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_conversation_user ON conversation_history(user_id);
CREATE INDEX idx_conversation_workspace ON conversation_history(workspace_id);
CREATE INDEX idx_conversation_session ON conversation_history(session_id);
```

**用途**: 保存问答历史，用于上下文学习和质量分析。

## Milvus 向量集合

### Collection: document_chunks

```python
{
    "collection_name": "document_chunks",
    "schema": {
        "fields": [
            {"name": "id", "type": "VARCHAR", "max_length": 100},
            {"name": "document_id", "type": "VARCHAR", "max_length": 100},
            {"name": "workspace_id", "type": "VARCHAR", "max_length": 100},
            {"name": "chunk_index", "type": "INT64"},
            {"name": "content", "type": "VARCHAR", "max_length": 65535},
            {"name": "embedding", "type": "FLOAT_VECTOR", "dim": 1536},
            {"name": "metadata", "type": "JSON"}
        ],
        "primary_key": "id"
    },
    "index": {
        "field_name": "embedding",
        "index_type": "HNSW",
        "metric_type": "COSINE",
        "params": {"M": 8, "efConstruction": 200}
    }
}
```

**关键配置**:
- **维度**: 1536 (OpenAI embeddings)
- **相似度度量**: COSINE (余弦相似度)
- **索引类型**: HNSW (高效近似最近邻搜索)

## 数据访问层 (DAO)

### DocumentDAO

```python
class DocumentDAO:
    def create_document(self, workspace_id: str, filename: str, ...) -> Document:
        """创建文档记录"""
        
    def update_document_status(self, document_id: str, status: str, ...):
        """更新文档状态"""
        
    def add_chunks(self, document_id: str, chunks: List[Dict], embeddings: List):
        """添加文档分块到 PostgreSQL + Milvus"""
        
    def delete_document(self, document_id: str):
        """删除文档及其分块"""
        
    def get_workspace_documents(self, workspace_id: str) -> List[Document]:
        """获取工作空间下的所有文档"""
```

### WorkspaceDAO

```python
class WorkspaceDAO:
    def create_workspace(self, name: str, owner_id: str, ...) -> Workspace:
        """创建工作空间"""
        
    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """获取工作空间"""
        
    def get_user_workspaces(self, user_id: str) -> List[Workspace]:
        """获取用户的所有工作空间"""
        
    def delete_workspace(self, workspace_id: str):
        """删除工作空间（级联删除文档）"""
```

### RetrieverService

```python
class RetrieverService:
    def similarity_search(
        self,
        query_vector: List[float],
        workspace_id: str,
        k: int = 5,
        filter_expr: str = None
    ) -> List[Dict]:
        """向量相似度搜索"""
        
    def hybrid_search(
        self,
        query_vector: List[float],
        workspace_id: str,
        k: int = 5,
        filters: Dict = None
    ) -> List[Dict]:
        """混合检索：向量 + SQL 过滤"""
```

## 外键约束与数据一致性

### 级联删除规则

```
users (删除) 
  └─ CASCADE → workspaces
       └─ CASCADE → documents
            └─ CASCADE → document_chunks
            
workspaces (删除)
  └─ CASCADE → documents
       └─ CASCADE → document_chunks
  └─ CASCADE → notes
```

### 触发器：自动更新 updated_at

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## 性能优化建议

### 1. 索引策略

```sql
-- 高频查询字段必须建立索引
CREATE INDEX idx_documents_workspace ON documents(workspace_id);
CREATE INDEX idx_chunks_document ON document_chunks(document_id);

-- 组合索引（如果经常一起查询）
CREATE INDEX idx_docs_workspace_status ON documents(workspace_id, status);

-- JSONB 索引（用于元数据查询）
CREATE INDEX idx_chunks_metadata ON document_chunks USING GIN (metadata);
```

### 2. 连接池配置

```python
# database/db_connection.py
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,         # 连接池大小
    max_overflow=40,      # 最大溢出连接数
    pool_pre_ping=True,   # 自动检测失效连接
    pool_recycle=3600,    # 1 小时回收连接
)
```

### 3. 批量操作

```python
# 批量插入分块（而不是逐个插入）
def add_chunks_batch(self, chunks_data: List[Dict]):
    self.db.bulk_insert_mappings(DocumentChunk, chunks_data)
    self.db.commit()
```

## 常见问题排查

### Q1: 外键约束错误

**错误**: `insert or update on table "documents" violates foreign key constraint`

**原因**: workspace_id 在 workspaces 表中不存在

**解决**:
```python
# 确保先创建工作空间记录
workspace = workspace_dao.create_workspace(name, owner_id)
workspace_id = str(workspace.id)

# 再使用该 ID 创建文档
doc = doc_dao.create_document(workspace_id=workspace_id, ...)
```

### Q2: 向量检索慢

**优化方案**:
1. 检查 Milvus 索引是否创建
2. 使用 HNSW 等高效索引类型
3. 限制检索范围（通过 workspace_id 过滤）
4. 减少 k 值（返回结果数量）

### Q3: 数据库连接超时

**解决**:
```python
# 增加连接超时时间
engine = create_engine(
    DATABASE_URL,
    connect_args={"connect_timeout": 30}
)
```

## 数据库迁移

### 使用 Alembic 进行迁移（推荐）

```bash
# 安装 Alembic
pip install alembic

# 初始化
alembic init alembic

# 创建迁移
alembic revision --autogenerate -m "Initial schema"

# 应用迁移
alembic upgrade head
```

### 手动执行 SQL 脚本

```bash
psql -h localhost -U codemind -d codemind -f database/init/001_init_schema.sql
```

## 备份与恢复

### 备份 PostgreSQL

```bash
pg_dump -h localhost -U codemind codemind > backup_$(date +%Y%m%d).sql
```

### 恢复 PostgreSQL

```bash
psql -h localhost -U codemind codemind < backup_20240324.sql
```

### 备份 Milvus

参考 [Milvus 官方文档](https://milvus.io/docs/manage_Data.md)

## 监控与告警

### 关键指标

1. **数据库连接数**
2. **查询响应时间**
3. **Milvus 检索延迟**
4. **磁盘使用率**

### Prometheus + Grafana 监控

```yaml
# docker-compose.yml 中添加
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
    
grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
```

## 安全最佳实践

1. **密码加密**: 使用 bcrypt 或 argon2
2. **SQL 注入防护**: 使用 ORM 的参数化查询
3. **访问控制**: 基于角色的权限管理 (RBAC)
4. **审计日志**: 记录所有敏感操作
5. **数据加密**: 敏感字段加密存储
