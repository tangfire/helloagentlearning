"""
基于 LangChain 的高级智能文档问答助手
整合 MarkItDown、多层次记忆系统、MQE 和 HyDE 高级检索
"""

import os
import dotenv
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
import hashlib

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# MarkItDown for document conversion
from markitdown import MarkItDown

# 导入记忆系统
from memory_system import MemoryManager, MemoryType, EpisodicMemory, SemanticMemory

# 加载环境变量
dotenv.load_dotenv()


class AdvancedPDFLearningAssistant:
    """
    高级智能文档问答助手
    
    核心功能：
    1. 智能文档处理：MarkItDown PDF->Markdown，基于 Markdown 结构的智能分块
    2. 高级检索：MQE 多查询扩展，HyDE 假设文档嵌入
    3. 多层次记忆：工作记忆、情景记忆、语义记忆、感知记忆
    4. 个性化学习：推荐、遗忘机制、学习报告
    """

    def __init__(self, user_id: str = "default_user"):
        """初始化学习助手"""
        self.user_id = user_id
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 初始化 LLM
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL", "gpt-3.5-turbo"),
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("BASE_URL"),
        )
        
        # 初始化 Embeddings
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("BASE_URL"),
        )
        
        # MarkItDown 文档转换器
        self.markitdown = MarkItDown()
        
        # 智能文本分割器 - 基于 Markdown 结构
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=[
                "\n## ",      # H2 标题
                "\n### ",     # H3 标题
                "\n#### ",    # H4 标题
                "\n\n",       # 段落
                "\n",         # 换行
                "。",         # 句号
                "！",         # 感叹号
                "？",         # 问号
                " ",         # 空格
                ""           # 字符级别
            ]
        )
        
        # 记忆管理器
        self.memory_manager = MemoryManager(user_id=user_id)
        
        # 向量存储
        self.vectorstore: Optional[FAISS] = None
        self.retriever = None
        
        # 文档元数据
        self.documents_metadata: Dict[str, Any] = {}
        
        # 学习统计
        self.stats = {
            "session_start": datetime.now(),
            "documents_loaded": 0,
            "questions_asked": 0,
            "chunks_created": 0,
            "mqe_queries_generated": 0,
            "hyde_hypotheses_generated": 0,
            "memories_created": 0
        }

    # ==================== 第一步：智能文档处理 ====================
    
    def load_document(self, file_path: str, 
                     enable_mqe: bool = True,
                     enable_hyde: bool = True) -> bool:
        """
        步骤 1：智能文档处理 + 记录到记忆系统
        
        Args:
            file_path: 文件路径
            enable_mqe: 是否启用 MQE（多查询扩展）
            enable_hyde: 是否启用 HyDE（假设文档嵌入）
        """
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"错误：文件不存在 - {file_path}")
                return False
            
            print(f"\n📄 开始处理文档：{path.name}")
            
            # 1.1 使用 MarkItDown 转换为 Markdown
            print("  → 使用 MarkItDown 转换文档...")
            markdown_result = self.markitdown.convert(str(path))
            markdown_text = markdown_result.markdown
            
            # 1.2 创建文档对象
            from langchain_core.documents import Document
            doc = Document(
                page_content=markdown_text,
                metadata={
                    "source": str(path),
                    "user_id": self.user_id,
                    "filename": path.name,
                    "file_size": path.stat().st_size,
                    "load_time": datetime.now().isoformat()
                }
            )
            
            # 1.3 基于 Markdown 结构的智能分块
            print("  → 智能分块...")
            chunks = self.text_splitter.split_documents([doc])
            
            # 1.4 添加元数据到每个 chunk
            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_id"] = f"{path.stem}_{i}"
                chunk.metadata["total_chunks"] = len(chunks)
            
            # 1.5 创建或更新向量存储
            if self.vectorstore is None:
                print("  → 创建向量索引...")
                self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
            else:
                print("  → 添加到向量索引...")
                self.vectorstore.add_documents(chunks)
            
            # 1.6 创建检索器
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )
            
            # 1.7 更新统计
            self.stats["documents_loaded"] += 1
            self.stats["chunks_created"] += len(chunks)
            
            # 1.8 记录文档元数据
            doc_id = hashlib.md5(str(path).encode()).hexdigest()
            self.documents_metadata[doc_id] = {
                "path": str(path),
                "name": path.name,
                "chunks": len(chunks),
                "load_time": datetime.now()
            }
            
            # 1.9 【步骤 1】记录到记忆系统 - 感知记忆（文档特征）
            self._record_document_to_memory(path, chunks)
            
            print(f"\n✅ 成功加载文档：{path.name}")
            print(f"   - 文本块数量：{len(chunks)}")
            print(f"   - 累计文档数：{self.stats['documents_loaded']}")
            
            return True
            
        except Exception as e:
            print(f"❌ 加载文档失败：{e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _record_document_to_memory(self, path: Path, chunks: List):
        """记录文档到记忆系统（步骤 1）"""
        # 1. 感知记忆：文档的物理特征
        self.memory_manager.add_perceptual_memory(
            document_id=path.stem,
            feature_type="document_structure",
            description=f"文档 {path.name} 包含 {len(chunks)} 个文本块",
            page=0
        )
        
        # 2. 创建工作记忆任务
        task_id = f"load_{path.stem}"
        self.memory_manager.create_working_memory(
            task_id=task_id,
            focus=f"加载文档：{path.name}"
        )
        
        # 3. 情景记忆：记录加载事件
        self.memory_manager.add_episodic_memory(
            event_type="document_load",
            query=f"加载文档 {path.name}",
            response=f"成功加载，共{len(chunks)}个文本块",
            sources=[str(path)],
            tags=["document_load", path.stem]
        )
        
        self.stats["memories_created"] += 3

    # ==================== 第二步：高级检索问答 ====================
    
    def ask(self, question: str, 
           use_mqe: bool = True,
           use_hyde: bool = True) -> dict:
        """
        步骤 2 & 4：高级检索 + 智能路由 + 记录到记忆
        
        Args:
            question: 问题
            use_mqe: 使用多查询扩展
            use_hyde: 使用假设文档嵌入
        """
        if self.vectorstore is None or self.retriever is None:
            return {
                "answer": "请先加载文档后再提问。",
                "sources": [],
                "retrieval_method": "none"
            }
        
        try:
            # 【步骤 2】创建工作记忆
            task_id = f"query_{datetime.now().strftime('%H%M%S')}"
            working_memory = self.memory_manager.create_working_memory(
                task_id=task_id,
                focus=f"回答问题：{question[:50]}..."
            )
            
            # 2.1 智能路由：选择检索策略
            retrieval_method = "basic"
            search_results = []
            
            if use_mqe and use_hyde:
                retrieval_method = "mqe+hyde"
                search_results = self._retrieve_with_mqe_and_hyde(question)
            elif use_mqe:
                retrieval_method = "mqe"
                search_results = self._retrieve_with_mqe(question)
            elif use_hyde:
                retrieval_method = "hyde"
                search_results = self._retrieve_with_hyde(question)
            else:
                search_results = self._basic_retrieve(question)
            
            # 2.2 格式化检索结果
            context = "\n\n".join([doc.page_content for doc in search_results])
            
            # 2.3 构建 RAG 链
            template = """使用以下上下文片段来回答问题。如果不知道答案，就说你不知道，不要编造答案。尽量给出详细和准确的回答。

上下文信息:
{context}

问题：{question}
有用回答:"""
            
            prompt = ChatPromptTemplate.from_template(template)
            
            rag_chain = (
                {"context": lambda x: context, "question": RunnablePassthrough()}
                | prompt
                | self.llm
                | StrOutputParser()
            )
            
            # 2.4 生成回答
            answer = rag_chain.invoke(question)
            
            # 2.5 更新统计
            self.stats["questions_asked"] += 1
            
            # 2.6 提取源文档信息
            sources = []
            for doc in search_results:
                sources.append({
                    "content": doc.page_content[:200] + "...",
                    "source": doc.metadata.get("source", "unknown"),
                    "page": doc.metadata.get("page", 0),
                    "chunk_id": doc.metadata.get("chunk_id", "unknown")
                })
            
            # 【步骤 2】记录检索结果到记忆系统
            self._record_retrieval_to_memory(
                question=question,
                answer=answer,
                sources=sources,
                retrieval_method=retrieval_method
            )
            
            response = {
                "answer": answer,
                "sources": sources,
                "question": question,
                "retrieval_method": retrieval_method,
                "num_sources": len(search_results)
            }
            
            return response
            
        except Exception as e:
            return {
                "answer": f"回答问题时出错：{e}",
                "sources": [],
                "retrieval_method": "error"
            }
    
    def _basic_retrieve(self, question: str) -> List:
        """基础检索"""
        return self.retriever.invoke(question)
    
    def _retrieve_with_mqe(self, question: str, num_queries: int = 3) -> List:
        """
        MQE（Multi-Query Embedding）多查询扩展检索
        生成多个相似查询，提高召回率
        """
        # 生成多个查询变体
        mqe_prompt = f"""基于以下问题，生成{num_queries}个不同但语义相似的查询变体：

原问题：{question}

请生成{num_queries}个变体（每行一个）："""
        
        mqe_response = self.llm.invoke(mqe_prompt).content
        queries = [q.strip() for q in mqe_response.split('\n') if q.strip()]
        
        self.stats["mqe_queries_generated"] += len(queries)
        
        # 对每个查询进行检索
        all_docs = []
        for query in queries[:num_queries]:  # 限制查询数量
            docs = self.retriever.invoke(query)
            all_docs.extend(docs)
        
        # 去重（基于内容哈希）
        seen = set()
        unique_docs = []
        for doc in all_docs:
            content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
            if content_hash not in seen:
                seen.add(content_hash)
                unique_docs.append(doc)
        
        return unique_docs[:10]  # 返回最多 10 个文档
    
    def _retrieve_with_hyde(self, question: str) -> List:
        """
        HyDE（Hypothetical Document Embedding）假设文档嵌入检索
        先生成假设性答案，再用答案检索
        """
        # 生成假设性文档
        hyde_prompt = f"""请为以下问题写一个详细的假设性答案（即使你可能不正确，尽量写得像真实文档）：

问题：{question}

假设性答案："""
        
        hypothetical_doc = self.llm.invoke(hyde_prompt).content
        self.stats["hyde_hypotheses_generated"] += 1
        
        # 用假设性文档进行检索
        docs = self.retriever.invoke(hypothetical_doc)
        return docs
    
    def _retrieve_with_mqe_and_hyde(self, question: str) -> List:
        """结合 MQE 和 HyDE 的检索"""
        # MQE 生成多个查询
        mqe_docs = self._retrieve_with_mqe(question, num_queries=2)
        
        # HyDE 生成假设文档并检索
        hyde_docs = self._retrieve_with_hyde(question)
        
        # 合并并去重
        all_docs = mqe_docs + hyde_docs
        seen = set()
        unique_docs = []
        for doc in all_docs:
            content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
            if content_hash not in seen:
                seen.add(content_hash)
                unique_docs.append(doc)
        
        return unique_docs[:10]
    
    def _record_retrieval_to_memory(self, 
                                   question: str,
                                   answer: str,
                                   sources: List[Dict],
                                   retrieval_method: str):
        """记录检索过程到记忆系统（步骤 2）"""
        source_paths = [s.get("source", "") for s in sources]
        
        # 1. 情景记忆：记录问答事件
        episodic_memory = self.memory_manager.add_episodic_memory(
            event_type="query_answer",
            query=question,
            response=answer,
            sources=source_paths,
            tags=["qa", retrieval_method, "learning"]
        )
        
        # 2. 更新工作记忆
        if self.memory_manager.current_working_memory:
            self.memory_manager.current_working_memory.add_context(
                f"Q: {question}\nA: {answer[:100]}..."
            )
        
        self.stats["memories_created"] += 1

    # ==================== 第三步：记忆系统管理 ====================
    
    def extract_semantic_memory(self, 
                               concept: str,
                               category: str = "general") -> Optional[SemanticMemory]:
        """
        步骤 3：从当前知识中提取语义记忆
        基于已有的问答历史，抽象出概念知识
        """
        # 搜索相关的情景记忆
        related_episodes = self.memory_manager.search_episodic_memories(
            query_keywords=concept,
            limit=5
        )
        
        if not related_episodes:
            return None
        
        # 从情景记忆中提取定义
        definitions = []
        for em in related_episodes:
            # 简单提取：从回答中抽取与概念相关的部分
            if concept.lower() in em.response.lower():
                definitions.append(em.response[:200])
        
        if not definitions:
            return None
        
        # 综合定义
        combined_definition = "\n\n".join(definitions[:2])
        
        # 创建语义记忆
        semantic_memory = self.memory_manager.add_semantic_memory(
            concept=concept,
            definition=combined_definition,
            category=category,
            source_documents=list(set(
                src for em in related_episodes for src in em.sources
            )),
            confidence=0.85
        )
        
        self.stats["memories_created"] += 1
        return semantic_memory
    
    def integrate_knowledge(self, topic: str) -> Dict[str, Any]:
        """
        步骤 3：记忆整合 - 整合同一主题的知识
        """
        # 搜索相关情景记忆
        episodes = self.memory_manager.search_episodic_memories(
            query_keywords=topic,
            limit=10
        )
        
        if len(episodes) < 2:
            return {"status": "insufficient_data", "episodes_found": len(episodes)}
        
        # 提取共同的知识点
        all_queries = [ep.query for ep in episodes]
        all_responses = [ep.response for ep in episodes]
        
        # 使用 LLM 整合知识
        integration_prompt = f"""基于以下问题和回答，整合成一个完整的知识点总结：

问题列表:
{chr(10).join(all_queries)}

回答列表:
{chr(10).join(all_responses)}

请整合成一个连贯、完整的知识点总结（300-500 字）："""
        
        integrated_knowledge = self.llm.invoke(integration_prompt).content
        
        # 创建语义记忆
        semantic_memory = self.memory_manager.add_semantic_memory(
            concept=topic,
            definition=integrated_knowledge,
            category="integrated_knowledge",
            source_documents=list(set(
                src for ep in episodes for src in ep.sources
            )),
            confidence=0.9,
            related_concepts=[ep.id for ep in episodes]
        )
        
        return {
            "status": "success",
            "semantic_memory_id": semantic_memory.id,
            "integrated_from": len(episodes),
            "knowledge_summary": integrated_knowledge[:200] + "..."
        }
    
    def selective_forget(self, days_old: int = 30) -> Dict[str, int]:
        """
        步骤 3：选择性遗忘 - 清理低质量的旧记忆
        """
        forgotten = self.memory_manager.forget_old_memories(days_threshold=days_old)
        return forgotten

    # ==================== 第五步：学习报告 ====================
    
    def generate_learning_report(self, export_path: str = None) -> Dict[str, Any]:
        """
        步骤 5：生成完整的学习报告
        整合 RAG 和 Memory 的所有统计信息
        """
        # 从记忆系统获取报告
        memory_report = self.memory_manager.get_learning_report()
        
        # 整合 RAG 统计
        full_report = {
            **memory_report,
            "rag_statistics": {
                "documents_loaded": self.stats["documents_loaded"],
                "total_chunks": self.stats["chunks_created"],
                "questions_answered": self.stats["questions_asked"],
                "mqe_queries_generated": self.stats["mqe_queries_generated"],
                "hyde_hypotheses_generated": self.stats["hyde_hypotheses_generated"]
            },
            "session_info": {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "duration": str(datetime.now() - self.stats["session_start"])
            }
        }
        
        # 导出到文件
        if export_path:
            import json
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(full_report, f, ensure_ascii=False, indent=2)
            print(f"📊 学习报告已导出到：{export_path}")
        
        return full_report
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            **self.stats,
            "session_duration": datetime.now() - self.stats["session_start"],
            "loaded_files": list(self.documents_metadata.keys()),
            "total_memories": (
                len(self.memory_manager.episodic_memories) +
                len(self.memory_manager.semantic_memories) +
                len(self.memory_manager.perceptual_memories)
            )
        }
    
    def reset(self):
        """重置助手状态（保留记忆）"""
        self.vectorstore = None
        self.retriever = None
        self.documents_metadata = {}
        self.stats = {
            "session_start": datetime.now(),
            "documents_loaded": 0,
            "questions_asked": 0,
            "chunks_created": 0,
            "mqe_queries_generated": 0,
            "hyde_hypotheses_generated": 0,
            "memories_created": 0
        }
        print("✓ 助手已重置（记忆系统保留）")


# 使用示例
if __name__ == "__main__":
    print("=" * 80)
    print("🚀 基于 LangChain 的高级智能文档问答助手")
    print("   整合 MarkItDown + 多层次记忆 + MQE + HyDE")
    print("=" * 80)
    
    # 创建助手实例
    assistant = AdvancedPDFLearningAssistant(user_id="user_001")
    
    # 加载文档
    pdf_path = "Happy-LLM-0727.pdf"
    if not os.path.exists(pdf_path):
        pdf_path = "01_hello_agent/Happy-LLM-0727.pdf"
    
    if os.path.exists(pdf_path):
        print(f"\n📚 加载文档：{pdf_path}")
        assistant.load_document(pdf_path)
        
        # 测试不同类型的问答
        test_questions = [
            "这篇文档主要讲了什么内容？",
            "有哪些关键概念？",
            "能总结一下核心观点吗？"
        ]
        
        print("\n" + "=" * 80)
        print("🤔 开始问答测试")
        print("=" * 80)
        
        for i, q in enumerate(test_questions, 1):
            print(f"\n【问题{i}】{q}")
            result = assistant.ask(q, use_mqe=True, use_hyde=True)
            print(f"【回答】{result['answer'][:300]}...")
            print(f"【检索方法】{result['retrieval_method']}")
            print(f"【来源数量】{result['num_sources']} 个文档片段")
        
        # 生成学习报告
        print("\n" + "=" * 80)
        print("📊 生成学习报告")
        print("=" * 80)
        report = assistant.generate_learning_report("learning_report.json")
        
        print(f"\n统计信息:")
        print(f"  - 加载文档：{report['rag_statistics']['documents_loaded']}")
        print(f"  - 创建文本块：{report['rag_statistics']['total_chunks']}")
        print(f"  - 回答问题：{report['rag_statistics']['questions_answered']}")
        print(f"  - MQE 查询：{report['rag_statistics']['mqe_queries_generated']}")
        print(f"  - HyDE 假设：{report['rag_statistics']['hyde_hypotheses_generated']}")
        print(f"  - 总记忆数：{report['statistics']['total_episodic_memories'] + report['statistics']['total_semantic_memories']}")
        
    else:
        print(f"\n❌ 未找到 PDF 文件：{pdf_path}")
