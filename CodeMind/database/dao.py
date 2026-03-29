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
    Note, OperationLog, ConversationHistory,
    Enterprise, EnterpriseKnowledge, ReportTemplate, DiagnosticReport
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
                chunk_metadata=chunk_data.get('metadata', {}),
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


# ==================== 企业诊断平台 DAO ====================

class EnterpriseDAO:
    """企业数据访问对象"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_enterprise(self, name: str, code: str, owner_id: str,
                         industry: str = None, scale: str = None,
                         description: str = None) -> Enterprise:
        """创建企业记录"""
        enterprise = Enterprise(
            id=uuid.uuid4(),
            name=name,
            code=code,
            owner_id=owner_id,
            industry=industry,
            scale=scale,
            description=description
        )
        
        self.db.add(enterprise)
        self.db.commit()
        self.db.refresh(enterprise)
        
        return enterprise
    
    def get_enterprise(self, enterprise_id: str) -> Optional[Enterprise]:
        """获取企业信息"""
        return self.db.query(Enterprise).filter(Enterprise.id == enterprise_id).first()
    
    def get_enterprise_by_code(self, code: str) -> Optional[Enterprise]:
        """根据编码获取企业"""
        return self.db.query(Enterprise).filter(Enterprise.code == code).first()
    
    def get_user_enterprises(self, user_id: str) -> List[Enterprise]:
        """获取用户的所有企业"""
        return self.db.query(Enterprise).filter(
            Enterprise.owner_id == user_id,
            Enterprise.is_active == True
        ).all()
    
    def update_enterprise(self, enterprise_id: str, **kwargs) -> bool:
        """更新企业信息"""
        enterprise = self.get_enterprise(enterprise_id)
        if enterprise:
            for key, value in kwargs.items():
                if hasattr(enterprise, key):
                    setattr(enterprise, key, value)
            self.db.commit()
            return True
        return False
    
    def delete_enterprise(self, enterprise_id: str) -> bool:
        """删除企业（软删除）"""
        enterprise = self.get_enterprise(enterprise_id)
        if enterprise:
            enterprise.is_active = False
            self.db.commit()
            return True
        return False


class EnterpriseKnowledgeDAO:
    """企业知识库数据访问对象"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.milvus = get_milvus_client()
    
    def create_knowledge(self, enterprise_id: str, title: str,
                        content: str = None, file_path: str = None,
                        category: str = None, doc_type: str = None,
                        tags: List[str] = None) -> EnterpriseKnowledge:
        """创建企业知识记录"""
        knowledge = EnterpriseKnowledge(
            id=uuid.uuid4(),
            enterprise_id=enterprise_id,
            title=title,
            content=content,
            file_path=file_path,
            category=category,
            doc_type=doc_type,
            tags=tags or []
        )
        
        self.db.add(knowledge)
        self.db.commit()
        self.db.refresh(knowledge)
        
        return knowledge
    
    def get_enterprise_knowledge(self, enterprise_id: str, 
                                 category: str = None) -> List[EnterpriseKnowledge]:
        """获取企业的知识库"""
        query = self.db.query(EnterpriseKnowledge).filter(
            EnterpriseKnowledge.enterprise_id == enterprise_id
        )
        
        if category:
            query = query.filter(EnterpriseKnowledge.category == category)
        
        return query.order_by(EnterpriseKnowledge.created_at.desc()).all()
    
    def search_knowledge(self, enterprise_id: str, keywords: str) -> List[EnterpriseKnowledge]:
        """搜索企业知识库"""
        return self.db.query(EnterpriseKnowledge).filter(
            EnterpriseKnowledge.enterprise_id == enterprise_id,
            EnterpriseKnowledge.content.ilike(f'%{keywords}%')
        ).all()
    
    def delete_knowledge(self, knowledge_id: str) -> bool:
        """删除知识记录"""
        knowledge = self.db.query(EnterpriseKnowledge).filter(
            EnterpriseKnowledge.id == knowledge_id
        ).first()
        if knowledge:
            self.db.delete(knowledge)
            self.db.commit()
            return True
        return False


class ReportTemplateDAO:
    """报告模板数据访问对象"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_template(self, name: str, category: str, template_type: str,
                       structure: List[Dict] = None, prompt_template: str = None,
                       description: str = None, created_by: str = None) -> ReportTemplate:
        """创建报告模板"""
        template = ReportTemplate(
            id=uuid.uuid4(),
            name=name,
            description=description,
            category=category,
            template_type=template_type,
            structure=structure or [],
            prompt_template=prompt_template,
            created_by=created_by
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        return template
    
    def get_template(self, template_id: str) -> Optional[ReportTemplate]:
        """获取报告模板"""
        return self.db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    
    def get_templates_by_category(self, category: str) -> List[ReportTemplate]:
        """获取某类别的所有模板"""
        return self.db.query(ReportTemplate).filter(
            ReportTemplate.category == category
        ).all()
    
    def get_default_templates(self) -> List[ReportTemplate]:
        """获取默认模板"""
        return self.db.query(ReportTemplate).filter(
            ReportTemplate.is_default == True
        ).all()


class DiagnosticReportDAO:
    """诊断报告数据访问对象"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def create_report(self, enterprise_id: str, title: str,
                     template_id: str = None, report_type: str = 'comprehensive',
                     analysis_query: str = None, generated_by: str = None) -> DiagnosticReport:
        """创建诊断报告"""
        report = DiagnosticReport(
            id=uuid.uuid4(),
            enterprise_id=enterprise_id,
            template_id=template_id,
            title=title,
            report_type=report_type,
            analysis_query=analysis_query,
            generated_by=generated_by,
            status='draft'
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        return report
    
    def get_report(self, report_id: str) -> Optional[DiagnosticReport]:
        """获取诊断报告"""
        return self.db.query(DiagnosticReport).filter(
            DiagnosticReport.id == report_id
        ).first()
    
    def get_enterprise_reports(self, enterprise_id: str) -> List[DiagnosticReport]:
        """获取企业的所有报告"""
        return self.db.query(DiagnosticReport).filter(
            DiagnosticReport.enterprise_id == enterprise_id
        ).order_by(DiagnosticReport.created_at.desc()).all()
    
    def update_report_status(self, report_id: str, status: str, 
                            error_message: str = None) -> bool:
        """更新报告状态"""
        report = self.get_report(report_id)
        if report:
            report.status = status
            if error_message:
                report.error_message = error_message
            if status == 'completed':
                report.completed_at = datetime.now()
            elif status == 'generating':
                report.started_at = datetime.now()
            self.db.commit()
            return True
        return False
    
    def update_report_content(self, report_id: str, 
                             llm_analysis: str = None,
                             conclusions: List = None,
                             recommendations: List = None,
                             ppt_file_path: str = None) -> bool:
        """更新报告内容"""
        report = self.get_report(report_id)
        if report:
            if llm_analysis:
                report.llm_analysis = llm_analysis
            if conclusions is not None:
                report.conclusions = conclusions
            if recommendations is not None:
                report.recommendations = recommendations
            if ppt_file_path:
                report.ppt_file_path = ppt_file_path
            self.db.commit()
            return True
        return False
