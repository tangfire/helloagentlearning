"""
ORM Models - 数据库模型定义

使用 SQLAlchemy 定义 PostgreSQL 数据库表结构
"""

from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, Text, ForeignKey, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, INET
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='user', 
                  check_constraint="role IN ('user', 'admin')")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    workspaces = relationship("Workspace", back_populates="owner")
    documents = relationship("Document", back_populates="uploader")
    notes = relationship("Note", back_populates="user")
    operation_logs = relationship("OperationLog", back_populates="user")
    conversation_history = relationship("ConversationHistory", back_populates="user")
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"


class Workspace(Base):
    """工作空间表"""
    __tablename__ = 'workspaces'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    owner = relationship("User", back_populates="workspaces")
    documents = relationship("Document", back_populates="workspace", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="workspace")
    
    def __repr__(self):
        return f"<Workspace(name='{self.name}')>"


class Document(Base):
    """文档表"""
    __tablename__ = 'documents'
    __table_args__ = (
        CheckConstraint("status IN ('processing', 'indexed', 'failed')", name='check_document_status'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True)
    filename = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255))
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    mime_type = Column(String(100))
    uploader_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    status = Column(String(20), default='processing', index=True)
    error_message = Column(Text)
    tags = Column(ARRAY(String))
    doc_metadata = Column('metadata', JSONB, default={})  # Python 属性名 doc_metadata，数据库列名 metadata
    version = Column(Integer, default=1)
    
    # 关系
    workspace = relationship("Workspace", back_populates="documents")
    uploader = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(filename='{self.filename}', status='{self.status}')>"


class DocumentChunk(Base):
    """文档分块表（带向量嵌入）"""
    __tablename__ = 'document_chunks'
    __table_args__ = (
        UniqueConstraint('document_id', 'chunk_index', name='uq_doc_chunk'),
        Index('idx_chunks_document', 'document_id'),
        Index('idx_chunks_metadata', 'metadata', postgresql_using='gin'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    # 注意：vector 类型需要 pgvector 扩展，这里用 Text 暂存，实际向量存储在 Milvus
    embedding = Column(Text)  # 可以存储为 JSON 数组或 Base64 编码
    chunk_metadata = Column('metadata', JSONB, default={})  # Python 属性名 chunk_metadata，数据库列名 metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    document = relationship("Document", back_populates="chunks")
    
    def __repr__(self):
        return f"<DocumentChunk(document_id='{self.document_id}', index={self.chunk_index})>"


class Note(Base):
    """笔记表（任务、决策、问题）"""
    __tablename__ = 'notes'
    __table_args__ = (
        CheckConstraint("note_type IN ('note', 'task', 'decision', 'question')", name='check_note_type'),
        CheckConstraint("status IN ('open', 'completed', 'archived')", name='check_note_status'),
        CheckConstraint("priority IN ('low', 'medium', 'high')", name='check_note_priority'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.id', ondelete='CASCADE'), index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    note_type = Column(String(20), default='note', index=True)
    status = Column(String(20), default='open', index=True)
    priority = Column(String(10), default='medium')
    tags = Column(ARRAY(String))
    note_metadata = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    workspace = relationship("Workspace", back_populates="notes")
    user = relationship("User", back_populates="notes")
    
    def __repr__(self):
        return f"<Note(title='{self.title}', type='{self.note_type}')>"


class OperationLog(Base):
    """操作日志表"""
    __tablename__ = 'operation_logs'
    __table_args__ = (
        CheckConstraint("""action IN (
            'UPLOAD_DOCUMENT', 'DELETE_DOCUMENT', 'ASK_QUESTION', 
            'CREATE_NOTE', 'EXECUTE_COMMAND', 'SWITCH_WORKSPACE'
        )""", name='check_log_action'),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.id'), index=True)
    action = Column(String(50), nullable=False, index=True)
    target_type = Column(String(50))
    target_id = Column(UUID(as_uuid=True))
    details = Column(JSONB, default={})
    ip_address = Column(INET)
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # 关系
    user = relationship("User", back_populates="operation_logs")
    workspace = relationship("Workspace")
    
    def __repr__(self):
        return f"<OperationLog(action='{self.action}', user_id='{self.user_id}')>"


class ConversationHistory(Base):
    """会话历史表"""
    __tablename__ = 'conversation_history'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey('workspaces.id'), index=True)
    session_id = Column(String(100), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text)
    context_used = Column(JSONB, default=[])
    retrieval_strategy = Column(JSONB)
    quality_score = Column(String(3))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # 关系
    user = relationship("User", back_populates="conversation_history")
    
    def __repr__(self):
        return f"<ConversationHistory(session_id='{self.session_id}')>"


# ==================== 企业诊断平台新增模型 ====================

class Enterprise(Base):
    """企业信息表"""
    __tablename__ = 'enterprises'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    code = Column(String(50), unique=True, nullable=False, index=True)  # 企业唯一编码
    industry = Column(String(100))  # 行业
    scale = Column(String(50))  # 规模
    description = Column(Text)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    owner = relationship("User")
    knowledge_base = relationship("EnterpriseKnowledge", back_populates="enterprise", cascade="all, delete-orphan")
    reports = relationship("DiagnosticReport", back_populates="enterprise", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Enterprise(name='{self.name}', code='{self.code}')>"


class EnterpriseKnowledge(Base):
    """企业知识库表（存储企业专属资料）"""
    __tablename__ = 'enterprise_knowledge'
    __table_args__ = (
        Index('idx_knowledge_enterprise', 'enterprise_id'),
        Index('idx_knowledge_category', 'category'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enterprise_id = Column(UUID(as_uuid=True), ForeignKey('enterprises.id', ondelete='CASCADE'), nullable=False)
    title = Column(String(300), nullable=False)
    content = Column(Text)
    file_path = Column(String(500))
    category = Column(String(50), index=True)  # 分类：财务、人力、运营、技术等
    doc_type = Column(String(50))  # 文档类型：制度、报告、数据等
    tags = Column(ARRAY(String))
    knowledge_metadata = Column(JSONB, default={})
    version = Column(Integer, default=1)
    is_public = Column(Boolean, default=False)  # 是否公开共享
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    enterprise = relationship("Enterprise", back_populates="knowledge_base")
    
    def __repr__(self):
        return f"<EnterpriseKnowledge(title='{self.title}', category='{self.category}')>"


class ReportTemplate(Base):
    """诊断报告模板表"""
    __tablename__ = 'report_templates'
    __table_args__ = (
        Index('idx_template_category', 'category'),
        Index('idx_template_type', 'template_type'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50), index=True)  # 模板分类
    template_type = Column(String(50), index=True)  # 模板类型：综合、专项等
    structure = Column(JSONB, default=[])  # 报告结构定义
    prompt_template = Column(Text)  # LLM 提示词模板
    ppt_template = Column(String(500))  # PPT 模板文件路径
    is_default = Column(Boolean, default=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    creator = relationship("User")
    
    def __repr__(self):
        return f"<ReportTemplate(name='{self.name}', type='{self.template_type}')>"


class DiagnosticReport(Base):
    """诊断分析报告表"""
    __tablename__ = 'diagnostic_reports'
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'generating', 'completed', 'failed')", name='check_report_status'),
        Index('idx_report_enterprise', 'enterprise_id'),
        Index('idx_report_status', 'status'),
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    enterprise_id = Column(UUID(as_uuid=True), ForeignKey('enterprises.id', ondelete='CASCADE'), nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey('report_templates.id'))
    title = Column(String(300), nullable=False)
    report_type = Column(String(50), default='comprehensive')  # 报告类型
    status = Column(String(20), default='draft', index=True)
    analysis_query = Column(Text)  # 分析查询条件/需求
    llm_analysis = Column(Text)  # LLM 生成的分析内容
    conclusions = Column(JSONB, default=[])  # 结论列表
    recommendations = Column(JSONB, default=[])  # 建议列表
    ppt_file_path = Column(String(500))  # 生成的 PPT 文件路径
    pdf_file_path = Column(String(500))  # 生成的 PDF 文件路径
    report_metadata = Column(JSONB, default={})
    generated_by = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    enterprise = relationship("Enterprise", back_populates="reports")
    template = relationship("ReportTemplate")
    generator = relationship("User")
    
    def __repr__(self):
        return f"<DiagnosticReport(title='{self.title}', status='{self.status}')>"
