"""
数据访问对象 - Data Access Objects

封装对 PostgreSQL 和 Milvus 的所有数据库操作
提供统一的业务逻辑接口
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import text

# 导入 ORM 模型
from database.models import (
    User, Workspace, Document, DocumentChunk, 
    Note, OperationLog, ConversationHistory
)
from database.milvus_client import get_milvus_client


class DocumentDAO:
    """文档数据访问对象"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.milvus = get_milvus_client()
    
    def create_document(self, workspace_id: str, filename: str, file_path: str,
                       file_size: int, uploader_id: str, mime_type: str = None,
                       original_filename: str = None) -> Document:
        """创建文档记录"""
        doc = Document(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            filename=filename,
            original_filename=original_filename or filename,
            file_path=file_path,
            file_size=file_size,
            mime_type=mime_type,
            uploader_id=uploader_id,
            status='processing'
        )
        
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        
        return doc
    
    def update_document_status(self, document_id: str, status: str, error_message: str = None):
        """更新文档状态"""
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.status = status
            if error_message:
                doc.error_message = error_message
            self.db.commit()
    
    def add_chunks(self, document_id: str, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        """
        添加文档分块到 PostgreSQL 和 Milvus
        
        Args:
            document_id: 文档 ID
            chunks: 分块列表，每个包含 content, metadata
            embeddings: 对应的向量列表
        """
        # 获取文档信息
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")
        
        # 准备 Milvus 数据
        milvus_data = []
        
        for i, (chunk_data, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = uuid.uuid4()
            
            # 添加到 PostgreSQL
            pg_chunk = DocumentChunk(
                id=chunk_id,
                document_id=document_id,
                chunk_index=i,
                content=chunk_data['content'],
                doc_metadata=chunk_data.get('metadata', {}),
                embedding=str(embedding)  # 临时存储为字符串
            )
            self.db.add(pg_chunk)
            
            # 准备 Milvus 数据
            milvus_data.append({
                "id": str(chunk_id),
                "document_id": str(document_id),
                "workspace_id": str(doc.workspace_id),
                "chunk_index": i,
                "content": chunk_data['content'],
                "embedding": embedding,
                "metadata": chunk_data.get('metadata', {})
            })
        
        # 提交 PostgreSQL
        self.db.commit()
        
        # 插入 Milvus
        result = self.milvus.insert_vectors(milvus_data)
        
        if not result.get('success'):
            # 如果 Milvus 失败，回滚 PostgreSQL
            self.db.rollback()
            raise Exception(f"Milvus insertion failed: {result.get('error')}")
        
        # 更新文档状态
        self.update_document_status(document_id, 'indexed')
    
    def delete_document(self, document_id: str):
        """删除文档及其所有分块"""
        # 从 Milvus 删除
        self.milvus.delete_by_document_id(str(document_id))
        
        # 从 PostgreSQL 删除（级联会删除 chunks）
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if doc:
            self.db.delete(doc)
            self.db.commit()
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """获取文档信息"""
        return self.db.query(Document).filter(Document.id == document_id).first()
    
    def get_workspace_documents(self, workspace_id: str) -> List[Document]:
        """获取工作空间下的所有文档"""
        return self.db.query(Document).filter(
            Document.workspace_id == workspace_id
        ).order_by(Document.uploaded_at.desc()).all()


class WorkspaceDAO:
    """工作空间数据访问对象"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_workspace(self, name: str, owner_id: str, description: str = None) -> Workspace:
        """创建工作空间"""
        workspace = Workspace(
            id=uuid.uuid4(),
            name=name,
            description=description,
            owner_id=owner_id
        )
        
        self.db.add(workspace)
        self.db.commit()
        self.db.refresh(workspace)
        
        return workspace
    
    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        """获取工作空间"""
        return self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
    
    def get_user_workspaces(self, user_id: str) -> List[Workspace]:
        """获取用户的所有工作空间"""
        return self.db.query(Workspace).filter(
            Workspace.owner_id == user_id,
            Workspace.is_active == True
        ).all()
    
    def delete_workspace(self, workspace_id: str):
        """删除工作空间（级联删除文档）"""
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if workspace:
            self.db.delete(workspace)
            self.db.commit()


class UserDAO:
    """用户数据访问对象"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户信息"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_default_user(self) -> Optional[User]:
        """获取默认管理员用户"""
        return self.db.query(User).filter(User.username == 'admin').first()


class OperationLogDAO:
    """操作日志数据访问对象"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def log_operation(self, user_id: str, action: str, workspace_id: str = None,
                     target_type: str = None, target_id: str = None, 
                     details: Dict = None, ip_address: str = None):
        """记录操作日志"""
        log = OperationLog(
            user_id=user_id,
            workspace_id=workspace_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
            ip_address=ip_address
        )
        
        self.db.add(log)
        self.db.commit()


class ConversationDAO:
    """会话历史数据访问对象"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def save_conversation(self, user_id: str, workspace_id: str, session_id: str,
                         question: str, answer: str, context_used: List = None,
                         retrieval_strategy: Dict = None, quality_score: float = None):
        """保存会话历史"""
        conversation = ConversationHistory(
            id=uuid.uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            session_id=session_id,
            question=question,
            answer=answer,
            context_used=context_used or [],
            retrieval_strategy=retrieval_strategy,
            quality_score=str(quality_score) if quality_score else None
        )
        
        self.db.add(conversation)
        self.db.commit()


class RetrieverService:
    """检索服务 - 混合向量检索"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.milvus = get_milvus_client()
    
    def similarity_search(
        self,
        query_vector: List[float],
        workspace_id: str,
        k: int = 5,
        filter_expr: str = None
    ) -> List[Dict[str, Any]]:
        """
        向量相似度搜索
        
        Args:
            query_vector: 查询向量
            workspace_id: 工作空间 ID（用于过滤）
            k: 返回结果数量
            filter_expr: 额外的过滤表达式
        
        Returns:
            搜索结果列表
        """
        # 从 Milvus 搜索
        results = self.milvus.search_vectors(
            query_vector=query_vector,
            workspace_id=workspace_id,
            limit=k,
            filter_expr=filter_expr
        )
        
        # 补充 PostgreSQL 中的元数据
        enriched_results = []
        for result in results:
            # 从 PostgreSQL 获取文档信息
            doc = self.db.query(Document).filter(
                Document.id == result['document_id']
            ).first()
            
            enriched_result = {
                **result,
                'document': {
                    'filename': doc.filename if doc else None,
                    'file_path': doc.file_path if doc else None,
                    'mime_type': doc.mime_type if doc else None
                } if doc else {}
            }
            enriched_results.append(enriched_result)
        
        return enriched_results
    
    def hybrid_search(
        self,
        query_vector: List[float],
        workspace_id: str,
        k: int = 5,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        混合检索：向量 + SQL 条件过滤
        
        Args:
            query_vector: 查询向量
            workspace_id: 工作空间 ID
            k: 返回结果数量
            filters: SQL 过滤条件字典
            
        Returns:
            检索结果
        """
        # 构建 Milvus 过滤表达式
        filter_parts = []
        
        if filters:
            for key, value in filters.items():
                if isinstance(value, str):
                    filter_parts.append(f"{key} == '{value}'")
                elif isinstance(value, (int, float)):
                    filter_parts.append(f"{key} == {value}")
                elif isinstance(value, list):
                    values_str = ', '.join([f"'{v}'" if isinstance(v, str) else str(v) for v in value])
                    filter_parts.append(f"{key} in [{values_str}]")
        
        filter_expr = ' and '.join(filter_parts) if filter_parts else None
        
        # 执行检索
        return self.similarity_search(
            query_vector=query_vector,
            workspace_id=workspace_id,
            k=k,
            filter_expr=filter_expr
        )
