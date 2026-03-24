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
