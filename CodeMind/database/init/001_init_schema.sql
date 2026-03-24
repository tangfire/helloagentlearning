-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- ========== 用户表 ==========
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- 创建索引
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- ========== 工作空间表 ==========
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- 创建索引
CREATE INDEX idx_workspaces_owner ON workspaces(owner_id);
CREATE INDEX idx_workspaces_name ON workspaces(name);

-- ========== 文档表 ==========
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
    tags TEXT[],  -- 标签数组
    metadata JSONB DEFAULT '{}'::jsonb,  -- 灵活的元数据
    version INTEGER DEFAULT 1  -- 版本号（支持文档版本控制）
);

-- 创建索引
CREATE INDEX idx_documents_workspace ON documents(workspace_id);
CREATE INDEX idx_documents_uploader ON documents(uploader_id);
CREATE INDEX idx_documents_filename ON documents(filename);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_tags ON documents USING GIN(tags);  -- GIN 索引用于数组查询
CREATE INDEX idx_documents_metadata ON documents USING GIN(metadata);  -- GIN 索引用于 JSONB 查询

-- ========== 文档分块表（带向量） ==========
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- OpenAI embeddings 维度
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_chunks_index ON document_chunks(chunk_index);
CREATE INDEX idx_chunks_metadata ON document_chunks USING GIN(metadata);

-- 向量索引（IVF 索引，适合大数据量）
-- 注意：需要先安装 pgvector 并设置合适的 lists 参数
CREATE INDEX idx_chunks_embedding ON document_chunks 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- 唯一约束
CREATE UNIQUE INDEX idx_chunks_unique ON document_chunks(document_id, chunk_index);

-- ========== 操作日志表 ==========
CREATE TABLE operation_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    workspace_id UUID REFERENCES workspaces(id),
    action VARCHAR(50) NOT NULL CHECK (action IN (
        'UPLOAD_DOCUMENT', 'DELETE_DOCUMENT', 'ASK_QUESTION', 
        'CREATE_NOTE', 'EXECUTE_COMMAND', 'SWITCH_WORKSPACE'
    )),
    target_type VARCHAR(50),  -- 操作对象类型
    target_id UUID,  -- 操作对象 ID
    details JSONB DEFAULT '{}'::jsonb,  -- 详细日志
    ip_address INET,  -- IP 地址
    user_agent TEXT,  -- 用户代理
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_logs_user ON operation_logs(user_id);
CREATE INDEX idx_logs_workspace ON operation_logs(workspace_id);
CREATE INDEX idx_logs_action ON operation_logs(action);
CREATE INDEX idx_logs_created_at ON operation_logs(created_at);
CREATE INDEX idx_logs_details ON operation_logs USING GIN(details);

-- ========== 笔记表（任务管理） ==========
CREATE TABLE notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    content TEXT,
    note_type VARCHAR(20) DEFAULT 'note' CHECK (note_type IN ('note', 'task', 'decision', 'question')),
    status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'completed', 'archived')),
    priority VARCHAR(10) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_notes_workspace ON notes(workspace_id);
CREATE INDEX idx_notes_user ON notes(user_id);
CREATE INDEX idx_notes_type ON notes(note_type);
CREATE INDEX idx_notes_status ON notes(status);
CREATE INDEX idx_notes_tags ON notes USING GIN(tags);

-- ========== 会话历史表 ==========
CREATE TABLE conversation_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    workspace_id UUID REFERENCES workspaces(id),
    session_id VARCHAR(100) NOT NULL,
    question TEXT NOT NULL,
    answer TEXT,
    context_used JSONB DEFAULT '[]'::jsonb,  -- 使用的上下文文档
    retrieval_strategy JSONB,  -- 检索策略配置
    quality_score DECIMAL(3,2),  -- 质量评分 0-1
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_conversation_user ON conversation_history(user_id);
CREATE INDEX idx_conversation_workspace ON conversation_history(workspace_id);
CREATE INDEX idx_conversation_session ON conversation_history(session_id);
CREATE INDEX idx_conversation_created_at ON conversation_history(created_at);

-- ========== 统计信息表（物化视图） ==========
CREATE MATERIALIZED VIEW workspace_stats AS
SELECT 
    w.id AS workspace_id,
    w.name AS workspace_name,
    COUNT(DISTINCT d.id) AS total_documents,
    COUNT(DISTINCT dc.id) AS total_chunks,
    COUNT(DISTINCT n.id) AS total_notes,
    COUNT(DISTINCT ch.id) AS total_conversations,
    MAX(d.uploaded_at) AS last_upload_time
FROM workspaces w
LEFT JOIN documents d ON w.id = d.workspace_id
LEFT JOIN document_chunks dc ON d.id = dc.document_id
LEFT JOIN notes n ON w.id = n.workspace_id
LEFT JOIN conversation_history ch ON w.id = ch.workspace_id
WHERE w.is_active = TRUE
GROUP BY w.id, w.name;

-- 创建索引
CREATE UNIQUE INDEX idx_workspace_stats_id ON workspace_stats(workspace_id);

-- ========== 触发器函数（自动更新 updated_at） ==========
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为需要自动更新的表添加触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notes_updated_at BEFORE UPDATE ON notes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========== 插入默认数据 ==========
-- 默认管理员用户（密码：admin123，实际使用时应该用 bcrypt 加密）
INSERT INTO users (id, username, email, password_hash, role) VALUES 
('00000000-0000-0000-0000-000000000001', 'admin', 'admin@codemind.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS3MebAJu', 'admin');

-- 默认工作空间
INSERT INTO workspaces (id, name, description, owner_id) VALUES 
('00000000-0000-0000-0000-000000000001', '默认工作空间', '系统自动创建的默认工作空间', '00000000-0000-0000-0000-000000000001');

-- ========== 注释 ==========
COMMENT ON TABLE users IS '用户表 - 存储系统用户信息';
COMMENT ON TABLE workspaces IS '工作空间表 - 多用户隔离的工作空间';
COMMENT ON TABLE documents IS '文档表 - 存储上传的文档元数据';
COMMENT ON TABLE document_chunks IS '文档分块表 - 存储文档切片和向量嵌入';
COMMENT ON TABLE operation_logs IS '操作日志表 - 记录所有用户操作';
COMMENT ON TABLE notes IS '笔记表 - 任务、决策、问题记录';
COMMENT ON TABLE conversation_history IS '会话历史表 - 记录问答历史';
COMMENT ON COLUMN document_chunks.embedding IS '向量嵌入 - 使用 OpenAI text-embedding-3-small (1536 维)';
COMMENT ON COLUMN documents.metadata IS '文档元数据 - JSONB 格式，支持灵活扩展';
COMMENT ON COLUMN operation_logs.details IS '操作详情 - JSONB 格式，记录额外信息';
