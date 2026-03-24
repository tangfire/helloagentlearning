"""
CodeMind Assistant - 数据库增强版

整合 PostgreSQL + Milvus 的生产级实现
支持持久化存储、混合检索和多用户隔离
"""

import os
import dotenv
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid

# 加载环境变量
dotenv.load_dotenv()

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

# 导入数据库层
from database.db_connection import get_db_context, SessionLocal
from database.dao import (
    DocumentDAO, WorkspaceDAO, UserDAO, 
    OperationLogDAO, ConversationDAO, RetrieverService
)
from database.models import User, Workspace, Document
from database.milvus_client import get_milvus_client

# MarkItDown for document conversion
from markitdown import MarkItDown


class CodeMindAssistantDB:
    """
    CodeMind Assistant - 数据库增强版
    
    核心特性：
    1. PostgreSQL 存储文档元数据和业务数据
    2. Milvus 存储向量数据
    3. 混合检索：向量相似度 + SQL 过滤
    4. 多用户隔离和工作空间管理
    5. 完整的操作日志和审计
    """
    
    def __init__(self, user_id: str = "admin", workspace_id: str = None):
        """
        初始化助手
        
        Args:
            user_id: 用户 ID
            workspace_id: 工作空间 ID
        """
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # LLM 和 Embeddings
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL", "gpt-4o-mini"),
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("BASE_URL"),
        )
        
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("BASE_URL"),
        )
        
        # 文档处理
        self.markitdown = MarkItDown()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        # 运行时向量存储（内存缓存）
        self.vectorstore: Optional[FAISS] = None
        self.retriever = None
        
        print(f"🚀 CodeMind Assistant DB 已初始化")
        print(f"   用户：{user_id}")
        print(f"   工作空间：{workspace_id or '默认'}")
        print(f"   会话 ID: {self.session_id}")
    
    def upload_document(self, file_path: str, filename: str = None) -> bool:
        """
        上传文档到数据库（PostgreSQL + Milvus）
        
        Args:
            file_path: 文件路径
            filename: 文件名（可选）
            
        Returns:
            是否成功上传
        """
        path = Path(file_path)
        if not path.exists():
            print(f"❌ 文件不存在：{file_path}")
            return False
        
        if not filename:
            filename = path.name
        
        try:
            with get_db_context() as db:
                # 初始化 DAO
                doc_dao = DocumentDAO(db)
                user_dao = UserDAO(db)
                log_dao = OperationLogDAO(db)
                
                # 获取用户
                user = user_dao.get_user(self.user_id)
                if not user:
                    user = user_dao.get_default_user()
                
                uploader_id = str(user.id) if user else "00000000-0000-0000-0000-000000000001"
                
                # 创建文档记录
                print(f"\n📄 创建文档记录：{filename}")
                doc = doc_dao.create_document(
                    workspace_id=self.workspace_id or "00000000-0000-0000-0000-000000000001",
                    filename=filename,
                    file_path=str(path),
                    file_size=path.stat().st_size,
                    uploader_id=uploader_id,
                    mime_type="text/plain"
                )
                
                # 处理文档内容
                print(f"   → 转换文档为 Markdown...")
                markdown_result = self.markitdown.convert(str(path))
                content = markdown_result.markdown
                
                # 分块
                print(f"   → 分块处理...")
                chunks = self.text_splitter.split_text(content)
                print(f"   → 创建了 {len(chunks)} 个文本块")
                
                # 生成向量
                print(f"   → 生成向量嵌入...")
                chunk_docs = [Document(page_content=chunk) for chunk in chunks]
                embeddings_list = self.embeddings.embed_documents([chunk.page_content for chunk in chunk_docs])
                
                # 准备分块数据
                chunks_data = []
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings_list)):
                    chunks_data.append({
                        'content': chunk,
                        'metadata': {
                            'chunk_index': i,
                            'total_chunks': len(chunks),
                            'filename': filename,
                            'source': str(path)
                        }
                    })
                
                # 保存到 PostgreSQL + Milvus
                print(f"   → 保存到数据库...")
                doc_dao.add_chunks(str(doc.id), chunks_data, embeddings_list)
                
                # 记录操作日志
                log_dao.log_operation(
                    user_id=uploader_id,
                    action='UPLOAD_DOCUMENT',
                    workspace_id=self.workspace_id,
                    target_type='document',
                    target_id=str(doc.id),
                    details={'filename': filename, 'chunks': len(chunks)}
                )
                
                print(f"✅ 文档上传成功：{filename}")
                print(f"   - 文档 ID: {doc.id}")
                print(f"   - 分块数：{len(chunks)}")
                
                return True
                
        except Exception as e:
            print(f"❌ 上传失败：{e}")
            import traceback
            traceback.print_exc()
            return False
    
    def search(self, query: str, k: int = 5, filters: Dict = None) -> List[Dict]:
        """
        混合检索：向量相似度 + SQL 过滤
        
        Args:
            query: 查询文本
            k: 返回结果数量
            filters: SQL 过滤条件
            
        Returns:
            检索结果列表
        """
        try:
            with get_db_context() as db:
                retriever = RetrieverService(db)
                
                # 生成查询向量
                query_vector = self.embeddings.embed_query(query)
                
                # 执行混合检索
                results = retriever.hybrid_search(
                    query_vector=query_vector,
                    workspace_id=self.workspace_id or "00000000-0000-0000-0000-000000000001",
                    k=k,
                    filters=filters
                )
                
                print(f"🔍 检索到 {len(results)} 个结果")
                
                return results
                
        except Exception as e:
            print(f"❌ 检索失败：{e}")
            return []
    
    def ask(self, question: str, use_context: bool = True) -> Dict[str, Any]:
        """
        智能问答
        
        Args:
            question: 问题
            use_context: 是否使用上下文
            
        Returns:
            回答和相关信息
        """
        try:
            with get_db_context() as db:
                # 检索相关文档
                context_docs = self.search(question, k=5)
                
                # 构建上下文
                context_text = ""
                sources = []
                
                if context_docs:
                    for i, doc in enumerate(context_docs, 1):
                        context_text += f"[{i}] {doc['content']}\n\n"
                        sources.append({
                            'filename': doc.get('document', {}).get('filename', 'Unknown'),
                            'chunk_index': doc.get('chunk_index', 0),
                            'score': doc.get('score', 0)
                        })
                
                # 构建提示词
                if use_context and context_text:
                    prompt = f"""基于以下上下文回答问题：

上下文：
{context_text}

问题：{question}

请根据上下文给出准确的回答："""
                else:
                    prompt = question
                
                # 调用 LLM
                response = self.llm.invoke(prompt)
                answer = response.content
                
                # 保存会话历史
                conv_dao = ConversationDAO(db)
                user_dao = UserDAO(db)
                user = user_dao.get_user(self.user_id)
                
                if user:
                    conv_dao.save_conversation(
                        user_id=str(user.id),
                        workspace_id=self.workspace_id or "00000000-0000-0000-0000-000000000001",
                        session_id=self.session_id,
                        question=question,
                        answer=answer,
                        context_used=[{'content': d['content']} for d in context_docs],
                        quality_score=0.8
                    )
                
                return {
                    'answer': answer,
                    'sources': sources,
                    'context_used': len(context_docs) > 0
                }
                
        except Exception as e:
            print(f"❌ 问答失败：{e}")
            return {
                'answer': f"发生错误：{str(e)}",
                'sources': [],
                'context_used': False
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            with get_db_context() as db:
                from sqlalchemy import text
                
                # 查询文档数
                result = db.execute(text("""
                    SELECT COUNT(*) FROM documents 
                    WHERE workspace_id = :workspace_id
                """), {'workspace_id': self.workspace_id or "00000000-0000-0000-0000-000000000001"})
                doc_count = result.scalar()
                
                # 查询分块数
                result = db.execute(text("""
                    SELECT COUNT(*) FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    WHERE d.workspace_id = :workspace_id
                """), {'workspace_id': self.workspace_id or "00000000-0000-0000-0000-000000000001"})
                chunk_count = result.scalar()
                
                # 查询 Milvus 集合统计
                milvus = get_milvus_client()
                milvus_stats = milvus.get_collection_stats()
                
                return {
                    'documents_loaded': doc_count or 0,
                    'chunks_created': chunk_count or 0,
                    'milvus_collection': milvus_stats.get('count', 0),
                    'questions_asked': 0,  # 可以从 conversation_history 查询
                    'notes_created': 0     # 可以从 notes 表查询
                }
                
        except Exception as e:
            print(f"❌ 获取统计失败：{e}")
            return {
                'documents_loaded': 0,
                'chunks_created': 0,
                'error': str(e)
            }
