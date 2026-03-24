"""
CodeMind Assistant - 代码库智能维护助手

整合了文档问答、代码库探索、任务追踪的长程智能体。
具备完整的上下文工程能力和多层次记忆系统。
"""

import os
import dotenv
import json
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
try:
    from .memory_system import MemoryManager, MemoryType, EpisodicMemory, SemanticMemory
except ImportError:
    from memory_system import MemoryManager, MemoryType, EpisodicMemory, SemanticMemory

# 导入新工具
try:
    from .note_tool import NoteTool
    from .context_builder import ContextBuilder
except ImportError:
    from note_tool import NoteTool
    from context_builder import ContextBuilder

# MCP 相关（可选）
try:
    from tools.terminal_tool import TerminalTool
    from tools.mcp_client import MCPClient
    MCP_AVAILABLE = True
except ImportError:
    try:
        from terminal_tool import TerminalTool
        from mcp_client import MCPClient
        MCP_AVAILABLE = True
    except ImportError:
        MCP_AVAILABLE = False
        print("⚠️  MCP 模块未安装，部分功能不可用")

# 加载环境变量 - 明确指定 .env 文件路径
from pathlib import Path as PathLib
env_path = PathLib(__file__).parent.parent / ".env"
print(f"🔑 加载环境变量：{env_path}")
dotenv.load_dotenv(dotenv_path=env_path)
print(f"   OPENAI_API_KEY: {'已配置' if os.getenv('OPENAI_API_KEY') else '未配置'}")
print(f"   MODEL: {os.getenv('MODEL', 'gpt-3.5-turbo')}")
print(f"   BASE_URL: {os.getenv('BASE_URL', 'https://api.openai.com/v1')}")


class CodeMindAssistant:
    """
    CodeMind Assistant - 代码库智能维护助手
    
    核心功能：
    1. 智能文档处理：PDF/TXT/代码文件 -> Markdown，基于结构的智能分块
    2. 代码库探索：TerminalTool 执行命令探索项目结构
    3. 高级检索：MQE 多查询扩展，HyDE 假设文档嵌入
    4. 任务管理：NoteTool 记录问题、决策、任务
    5. 上下文工程：ContextBuilder 智能筛选和组织跨会话上下文
    6. 多层次记忆：工作记忆、情景记忆、语义记忆、感知记忆
    7. 个性化学习：推荐、遗忘机制、学习报告
    """

    def __init__(self, 
                 user_id: str = "default_user",
                 project_path: Optional[str] = None,
                 notes_storage: Optional[str] = None):
        """
        初始化 CodeMind 助手
        
        Args:
            user_id: 用户 ID
            project_path: 项目路径（可选）
            notes_storage: 笔记存储路径（可选）
        """
        self.user_id = user_id
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.project_path = Path(project_path) if project_path else Path.cwd()
        
        # ========== LLM 和 Embeddings ==========
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL", "gpt-3.5-turbo"),
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("BASE_URL"),
        )
        
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_api_base=os.getenv("BASE_URL"),
        )
        
        # ========== 文档处理组件 ==========
        self.markitdown = MarkItDown()
        
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
        
        # ========== 记忆管理器 ==========
        self.memory_manager = MemoryManager(user_id=user_id)
        
        # ========== 向量存储 ==========
        self.vectorstore: Optional[FAISS] = None
        self.retriever = None
        
        # ========== 新工具组件 ==========
        # 笔记工具 - 记录长期任务
        self.note_tool = NoteTool(storage_path=notes_storage)
        
        # 终端工具 - 探索代码库
        self.terminal_tool = TerminalTool(working_dir=str(self.project_path))
        
        # 上下文构建器 - 管理跨会话上下文
        self.context_builder = ContextBuilder(max_context_length=8000)
        
        # ========== 元数据和统计 ==========
        self.documents_metadata: Dict[str, Any] = {}
        
        self.stats = {
            "session_start": datetime.now(),
            "documents_loaded": 0,
            "questions_asked": 0,
            "chunks_created": 0,
            "mqe_queries_generated": 0,
            "hyde_hypotheses_generated": 0,
            "memories_created": 0,
            "context_compressed": 0,
            "context_quality_scores": [],
            "commands_executed": 0,
            "notes_created": 0
        }
        
        # ========== 上下文工程配置 ==========
        self.compressor = None
        self.contextual_retriever = None
        self.max_context_length = 4000
        self.context_quality_threshold = 0.7
        
        print(f"🚀 CodeMind Assistant 已初始化")
        print(f"   用户：{user_id}")
        print(f"   项目路径：{self.project_path}")
        print(f"   会话 ID: {self.session_id}")
    
    def index_codebase(self, file_patterns: List[str] = ["*.py"], max_files: int = 20) -> bool:
        """
        索引项目代码库到向量数据库
        
        Args:
            file_patterns: 文件匹配模式列表，如 ["*.py", "*.md"]
            max_files: 最大索引文件数
            
        Returns:
            是否成功索引
        """
        try:
            from langchain_core.documents import Document
            import glob
            
            print(f"\n📂 开始索引项目代码库：{self.project_path}")
            
            # 收集所有匹配的文件
            all_files = []
            for pattern in file_patterns:
                files = glob.glob(str(self.project_path / "**" / pattern), recursive=True)
                all_files.extend(files)
            
            # 限制文件数量
            all_files = all_files[:max_files]
            print(f"   发现 {len(all_files)} 个文件")
            
            if not all_files:
                print("   ⚠️  没有找到可索引的文件")
                return False
            
            # 读取并处理每个文件
            documents = []
            for file_path in all_files:
                try:
                    path = Path(file_path)
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 创建文档对象
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": str(path),
                            "filename": path.name,
                            "file_type": path.suffix,
                            "file_size": path.stat().st_size,
                            "index_time": datetime.now().isoformat()
                        }
                    )
                    documents.append(doc)
                except Exception as e:
                    print(f"   ⚠️  跳过文件 {path.name}: {e}")
                    continue
            
            if not documents:
                print("   ❌ 没有可处理的文档")
                return False
            
            # 分块
            print("   → 分块处理...")
            chunks = self.text_splitter.split_documents(documents)
            print(f"   → 创建了 {len(chunks)} 个文本块")
            
            # 创建向量存储
            print("   → 创建向量索引...")
            self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
            
            # 创建检索器
            print("   → 创建检索器...")
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )
            
            # 初始化上下文压缩器
            self._initialize_context_compressor()
            
            # 更新统计
            self.stats["documents_loaded"] = len(documents)
            self.stats["chunks_created"] = len(chunks)
            
            print(f"\n✅ 代码库索引完成！")
            print(f"   - 索引文件数：{len(documents)}")
            print(f"   - 文本块数：{len(chunks)}")
            print(f"   - 可以开始提问了")
            
            # 自动保存向量索引
            self.save_vectorstore()
            
            return True
            
        except Exception as e:
            print(f"❌ 索引失败：{e}")
            import traceback
            traceback.print_exc()
            return False
    
    def save_vectorstore(self, save_path: Optional[Path] = None) -> bool:
        """
        保存向量索引到磁盘
        
        Args:
            save_path: 保存路径（可选，默认为项目路径下的 vectorstore 目录）
        """
        try:
            if self.vectorstore is None:
                print("⚠️  没有可保存的向量索引")
                return False
            
            if save_path is None:
                save_path = self.project_path / "vectorstore"
            
            save_path.mkdir(parents=True, exist_ok=True)
            
            print(f"💾 保存向量索引到：{save_path}")
            self.vectorstore.save_local(str(save_path))
            
            # 保存元数据
            metadata_file = save_path / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "project_path": str(self.project_path),
                    "user_id": self.user_id,
                    "documents_loaded": self.stats["documents_loaded"],
                    "chunks_created": self.stats["chunks_created"],
                    "saved_at": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 向量索引已保存")
            return True
            
        except Exception as e:
            print(f"❌ 保存向量索引失败：{e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_vectorstore(self, load_path: Optional[Path] = None) -> bool:
        """
        从磁盘加载向量索引
        
        Args:
            load_path: 加载路径（可选，默认为项目路径下的 vectorstore 目录）
        """
        try:
            if load_path is None:
                load_path = self.project_path / "vectorstore"
            
            if not load_path.exists():
                print(f"⚠️  向量索引不存在：{load_path}")
                return False
            
            print(f"📂 从 {load_path} 加载向量索引...")
            
            # 加载向量存储
            self.vectorstore = FAISS.load_local(
                str(load_path),
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            # 创建检索器
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}
            )
            
            # 加载元数据
            metadata_file = load_path / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    self.stats["documents_loaded"] = metadata.get("documents_loaded", 0)
                    self.stats["chunks_created"] = metadata.get("chunks_created", 0)
                    print(f"   📊 加载的文档数：{metadata.get('documents_loaded', 0)}")
                    print(f"   📊 加载的文本块数：{metadata.get('chunks_created', 0)}")
            
            # 初始化上下文压缩器
            self._initialize_context_compressor()
            
            print(f"✅ 向量索引加载成功！")
            return True
            
        except Exception as e:
            print(f"❌ 加载向量索引失败：{e}")
            import traceback
            traceback.print_exc()
            return False

    # ==================== 第一步：智能文档处理 ====================
    
    def load_document(self, file_path: str, 
                     enable_mqe: bool = True,
                     enable_hyde: bool = True) -> bool:
        """
        步骤 1：智能文档处理 + 记录到记忆系统
        
        Args:
            file_path: 文件路径
            enable_mqe: 是否启用 MQE
            enable_hyde: 是否启用 HyDE
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
            
            # 1.7 初始化上下文压缩器
            self._initialize_context_compressor()
            
            # 1.8 更新统计
            self.stats["documents_loaded"] += 1
            self.stats["chunks_created"] += len(chunks)
            
            # 1.9 记录文档元数据
            doc_id = hashlib.md5(str(path).encode()).hexdigest()
            self.documents_metadata[doc_id] = {
                "path": str(path),
                "name": path.name,
                "chunks": len(chunks),
                "load_time": datetime.now()
            }
            
            # 1.10 【步骤 1】记录到记忆系统
            self._record_document_to_memory(path, chunks)
            
            # 1.11 添加到上下文历史
            self.context_builder.add_entry(
                entry_type="note",
                content=f"加载文档：{path.name}，共{len(chunks)}个文本块",
                metadata={"document_id": doc_id}
            )
            
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
        """记录文档到记忆系统"""
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

    # ==================== 第二步：代码库探索 ====================
    
    def explore_codebase(self, 
                        command: str = "ls -la",
                        save_to_notes: bool = True) -> Dict[str, Any]:
        """
        探索代码库结构
        
        Args:
            command: shell 命令
            save_to_notes: 是否保存到笔记
            
        Returns:
            执行结果
        """
        print(f"\n💻 执行命令：{command}")
        
        result = self.terminal_tool.execute(command)
        
        self.stats["commands_executed"] += 1
        
        # 保存到笔记
        if save_to_notes and result["success"]:
            self.note_tool.create_note(
                title=f"代码库探索：{command}",
                content=result["stdout"],
                note_type="observation",
                tags=["codebase", "exploration"],
                priority="medium"
            )
            self.stats["notes_created"] += 1
        
        # 添加到上下文
        self.context_builder.add_entry(
            entry_type="terminal",
            content=result["stdout"] if result["success"] else result["stderr"],
            metadata={"command": command, "success": result["success"]}
        )
        
        return result
    
    def analyze_file(self, filepath: str) -> Dict[str, Any]:
        """
        分析文件
        
        Args:
            filepath: 文件路径
            
        Returns:
            文件分析结果
        """
        print(f"\n🔍 分析文件：{filepath}")
        
        # 获取文件统计
        file_stats = self.terminal_tool.get_file_stats(filepath)
        
        if "error" in file_stats:
            return file_stats
        
        # 查看文件内容
        content_preview = self.terminal_tool.view_file(filepath, lines=30)
        
        # 创建分析笔记
        analysis_note = self.note_tool.create_note(
            title=f"文件分析：{filepath}",
            content=f"文件统计:\n{json.dumps(file_stats, indent=2)}\n\n内容预览:\n{content_preview}",
            note_type="observation",
            tags=["file_analysis", filepath],
            related_files=[filepath],
            priority="medium"
        )
        
        self.stats["notes_created"] += 1
        
        # 添加到上下文
        self.context_builder.add_entry(
            entry_type="code_analysis",
            content=f"分析了文件 {filepath}: {file_stats.get('lines', -1)} 行，{file_stats.get('size_kb', 0)} KB",
            metadata={"filepath": filepath, "stats": file_stats}
        )
        
        return {
            "stats": file_stats,
            "preview": content_preview,
            "note_id": analysis_note.id
        }
    
    def search_in_codebase(self, 
                          pattern: str,
                          file_pattern: str = "*.py") -> str:
        """
        在代码库中搜索
        
        Args:
            pattern: 搜索模式
            file_pattern: 文件匹配模式
            
        Returns:
            搜索结果
        """
        print(f"\n🔎 搜索代码：'{pattern}' (匹配：{file_pattern})")
        
        result = self.terminal_tool.search_code(pattern, file_pattern)
        
        # 创建搜索笔记
        self.note_tool.create_note(
            title=f"代码搜索：{pattern}",
            content=result,
            note_type="observation",
            tags=["search", pattern, file_pattern],
            priority="high"
        )
        self.stats["notes_created"] += 1
        
        # 添加到上下文
        self.context_builder.add_entry(
            entry_type="code_analysis",
            content=result,
            metadata={"pattern": pattern, "file_pattern": file_pattern}
        )
        
        return result

    # ==================== 第三步：高级检索问答 ====================
    
    def ask(self, question: str, 
           use_mqe: bool = True,
           use_hyde: bool = True,
           use_context: bool = True) -> dict:
        """
        步骤 2 & 4：高级检索 + 智能路由 + 记录到记忆
        
        Args:
            question: 问题
            use_mqe: 使用多查询扩展
            use_hyde: 使用假设文档嵌入
            use_context: 使用历史上下文
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
            
            # 如果有历史上下文，先构建优化上下文
            context_str = ""
            if use_context:
                context_str = self.context_builder.build_context(question)
                if context_str:
                    print(f"\n📚 加载历史上下文 ({len(context_str)} 字符)")
            
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
            
            # 2.2 【上下文工程】质量评估、排序、压缩、自适应窗口
            print(f"\n🔍 检索到 {len(search_results)} 个文档片段")
            
            # 上下文质量评估
            quality_report = self._evaluate_context_quality(question, search_results)
            
            # 上下文排序
            search_results = self._rank_context_by_relevance(question, search_results)
            
            # 上下文压缩（如果文档数量过多）
            if len(search_results) > 5:
                search_results = self._compress_context(question, search_results)
            
            # 动态上下文窗口调整
            search_results = self._adapt_context_window(question, search_results)
            
            # 2.3 格式化检索结果
            context = "\n\n".join([doc.page_content for doc in search_results])
            
            # 2.4 构建 RAG 链（包含历史上下文）
            template = """使用以下上下文片段来回答问题。如果不知道答案，就说你不知道，不要编造答案。尽量给出详细和准确的回答。

{history_context}

当前检索到的上下文信息:
{context}

问题：{question}
有用回答:"""
            
            prompt = ChatPromptTemplate.from_template(template)
            
            rag_chain = (
                {"context": lambda x: context, 
                 "history_context": lambda x: context_str,
                 "question": RunnablePassthrough()}
                | prompt
                | self.llm
                | StrOutputParser()
            )
            
            # 2.5 生成回答
            print(f"\n🤖 正在生成回答...")
            print(f"   - LLM 模型：{self.llm.model_name}")
            print(f"   - Base URL: {self.llm.openai_api_base}")
            try:
                answer = rag_chain.invoke(question)
                print(f"   ✅ 回答生成成功，长度：{len(answer)}")
            except Exception as llm_error:
                print(f"   ❌ LLM 调用失败：{llm_error}")
                print(f"   错误类型：{type(llm_error).__name__}")
                import traceback
                traceback.print_exc()
                raise Exception(f"AI 模型调用失败：{llm_error}")
            
            # 2.6 更新统计
            self.stats["questions_asked"] += 1
            
            # 2.7 提取源文档信息
            sources = []
            for doc in search_results:
                sources.append({
                    "content": doc.page_content[:200] + "...",
                    "source": doc.metadata.get("source", "unknown"),
                    "page": doc.metadata.get("page", 0),
                    "chunk_id": doc.metadata.get("chunk_id", "unknown")
                })
            
            # 【步骤 2】记录检索过程到记忆系统
            self._record_retrieval_to_memory(
                question=question,
                answer=answer,
                sources=sources,
                retrieval_method=retrieval_method
            )
            
            # 记录到上下文历史
            self.context_builder.add_entry(
                entry_type="task_update",
                content=f"问答：{question[:100]}...\n回答：{answer[:200]}...",
                metadata={"method": retrieval_method, "sources": len(sources)}
            )
            
            response = {
                "answer": answer,
                "sources": sources,
                "question": question,
                "retrieval_method": retrieval_method,
                "num_sources": len(search_results),
                "context_used": bool(context_str)
            }
            
            return response
            
        except Exception as e:
            return {
                "answer": f"回答问题时出错：{e}",
                "sources": [],
                "retrieval_method": "error"
            }
    
    # ==================== 第四步：任务管理 ====================
    
    def create_task(self,
                   title: str,
                   description: str,
                   priority: str = "medium",
                   tags: Optional[List[str]] = None,
                   related_files: Optional[List[str]] = None) -> str:
        """
        创建任务
        
        Args:
            title: 任务标题
            description: 任务描述
            priority: 优先级
            tags: 标签
            related_files: 相关文件
            
        Returns:
            任务 ID
        """
        note = self.note_tool.create_note(
            title=title,
            content=description,
            note_type="task",
            tags=tags or [],
            related_files=related_files or [],
            priority=priority,
            status="open"
        )
        
        self.stats["notes_created"] += 1
        
        # 添加到上下文
        self.context_builder.add_entry(
            entry_type="task_update",
            content=f"创建任务：{title}\n{description}",
            metadata={"task_id": note.id, "priority": priority}
        )
        
        return note.id
    
    def update_task_status(self, 
                          task_id: str,
                          new_status: str,
                          comment: Optional[str] = None) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务 ID
            new_status: 新状态 (open/in_progress/resolved/closed)
            comment: 评论
            
        Returns:
            是否成功更新
        """
        success = self.note_tool.update_note(
            task_id,
            status=new_status,
            content=f"{self.note_tool.get_note(task_id).content}\n\n[状态更新]: {comment or ''}"
        )
        
        if success:
            # 记录到上下文
            self.context_builder.add_entry(
                entry_type="task_update",
                content=f"任务 {task_id} 状态更新为 {new_status}",
                metadata={"task_id": task_id, "status": new_status}
            )
        
        return success
    
    def get_task_summary(self) -> Dict[str, Any]:
        """获取任务摘要"""
        return self.note_tool.get_summary()
    
    # ==================== 第五步：知识整合与报告 ====================
    
    def generate_learning_report(self, output_path: str = "codemind_report.json") -> dict:
        """
        步骤 5：生成学习报告 + 导出笔记
        
        Args:
            output_path: 输出路径
            
        Returns:
            学习报告
        """
        print("\n📊 生成学习报告...")
        
        # 1. 从记忆系统获取报告
        report = self.memory_manager.get_learning_report()
        
        # 2. 添加笔记统计
        report["notes"] = self.note_tool.get_summary()
        
        # 3. 添加上下文统计
        report["context"] = self.context_builder.get_summary()
        
        # 4. 添加终端命令统计
        report["terminal"] = self.terminal_tool.get_stats_summary()
        
        # 5. 添加 RAG 统计
        report["rag_statistics"] = {
            "documents_loaded": self.stats["documents_loaded"],
            "chunks_created": self.stats["chunks_created"],
            "questions_asked": self.stats["questions_asked"],
            "mqe_queries_generated": self.stats["mqe_queries_generated"],
            "hyde_hypotheses_generated": self.stats["hyde_hypotheses_generated"],
            "avg_context_quality": (
                sum(self.stats["context_quality_scores"]) / len(self.stats["context_quality_scores"])
                if self.stats["context_quality_scores"] else 0.0
            )
        }
        
        # 6. 保存报告
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 学习报告已保存到：{output_path}")
        
        # 7. 导出所有笔记
        notes_path = output_path.replace('.json', '_notes.json')
        self.note_tool.export_notes(notes_path)
        
        return report
    
    def get_stats(self) -> dict:
        """获取统计信息（包含所有工具）"""
        # 计算平均上下文质量
        avg_quality = (
            sum(self.stats["context_quality_scores"]) / len(self.stats["context_quality_scores"])
            if self.stats["context_quality_scores"] else 0.0
        )
        
        return {
            **self.stats,
            "session_duration": datetime.now() - self.stats["session_start"],
            "loaded_files": list(self.documents_metadata.keys()),
            "total_memories": (
                len(self.memory_manager.episodic_memories) +
                len(self.memory_manager.semantic_memories) +
                len(self.memory_manager.perceptual_memories)
            ),
            "context_engineering": {
                "compressions_performed": self.stats["context_compressed"],
                "avg_context_quality": round(avg_quality, 3),
                "quality_threshold": self.context_quality_threshold,
                "max_context_length": self.max_context_length
            },
            "tools_usage": {
                "commands_executed": self.stats["commands_executed"],
                "notes_created": self.stats["notes_created"],
                "context_entries": len(self.context_builder.context_history)
            }
        }
    
    # ==================== MCP 集成功能 ====================
    
    def connect_to_mcp_server(self, server_name: str, 
                             command: Optional[str] = None,
                             args: Optional[List[str]] = None) -> bool:
        """
        连接到外部 MCP 服务器
        
        Args:
            server_name: 服务器名称（filesystem, git, database 等）
            command: 启动命令
            args: 命令参数
            
        Returns:
            连接是否成功
        """
        if not MCP_AVAILABLE:
            print("⚠️  MCP 模块不可用，请安装依赖：pip install mcp")
            return False
        
        import asyncio
        from mcp_client import MCPClient
        
        async def _connect():
            client = MCPClient()
            success = await client.connect_to_server(server_name, command, args)
            return client, success
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        mcp_client, success = loop.run_until_complete(_connect())
        
        if success:
            print(f"✅ 已连接到 MCP 服务器：{server_name}")
            # 保存客户端实例
            if not hasattr(self, 'mcp_clients'):
                self.mcp_clients = {}
            self.mcp_clients[server_name] = mcp_client
            
            # 记录到笔记
            self.note_tool.create_note(
                title=f"MCP 连接：{server_name}",
                content=f"连接到 MCP 服务器：{server_name}",
                note_type="observation",
                tags=["mcp", "integration"]
            )
        else:
            print(f"❌ 连接 MCP 服务器失败：{server_name}")
        
        return success
    
    async def call_mcp_tool(self, server_name: str, tool_name: str,
                           arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用外部 MCP 服务器的工具
        
        Args:
            server_name: 服务器名称
            tool_name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        if not MCP_AVAILABLE:
            return {
                "success": False,
                "error": "MCP 模块不可用"
            }
        
        if not hasattr(self, 'mcp_clients') or server_name not in self.mcp_clients:
            return {
                "success": False,
                "error": f"未连接到 MCP 服务器：{server_name}"
            }
        
        client = self.mcp_clients[server_name]
        result = await client.call_tool(server_name, tool_name, arguments)
        
        # 记录工具调用
        self.stats["commands_executed"] += 1
        
        return result
    
    def get_mcp_status(self) -> Dict[str, Any]:
        """
        获取 MCP 连接状态
        
        Returns:
            连接状态信息
        """
        if not MCP_AVAILABLE:
            return {"available": False}
        
        if not hasattr(self, 'mcp_clients'):
            return {
                "available": True,
                "connected_servers": 0,
                "servers": {}
            }
        
        status = {
            "available": True,
            "connected_servers": len(getattr(self, 'mcp_clients', {})),
            "servers": {}
        }
        
        for name, client in getattr(self, 'mcp_clients', {}).items():
            client_status = client.get_connection_status()
            status["servers"][name] = client_status
        
        return status
    
    def disconnect_mcp_server(self, server_name: Optional[str] = None):
        """
        断开 MCP 服务器连接
        
        Args:
            server_name: 服务器名称（可选，不传则断开所有连接）
        """
        if not hasattr(self, 'mcp_clients'):
            return
        
        import asyncio
        
        async def _disconnect(name: Optional[str]):
            if name:
                if name in self.mcp_clients:
                    await self.mcp_clients[name].disconnect(name)
                    del self.mcp_clients[name]
                    print(f"🔌 已断开 MCP 连接：{name}")
            else:
                for client_name in list(self.mcp_clients.keys()):
                    await self.mcp_clients[client_name].disconnect()
                self.mcp_clients.clear()
                print("🔌 已断开所有 MCP 连接")
        
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        loop.run_until_complete(_disconnect(server_name))
    
    def reset(self):
        """重置助手（保留记忆系统）"""
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
            "memories_created": 0,
            "context_compressed": 0,
            "context_quality_scores": [],
            "commands_executed": 0,
            "notes_created": 0
        }
        self.context_builder.clear_history()
        print("✓ 助手已重置（记忆系统和笔记保留）")
    
    # ==================== 辅助方法（MQE、HyDE、上下文工程等）====================
    
    def _generate_mqe_queries(self, question: str, num_queries: int = 3) -> List[str]:
        """生成多查询扩展"""
        prompt = ChatPromptTemplate.from_template(
            "你是一个问题扩展专家。请基于以下问题，生成{num}个不同角度的相关问题:\n\n原问题：{question}\n\n生成的问题:"
        )
        chain = prompt | self.llm | StrOutputParser()
        result = chain.invoke({"num": num_queries, "question": question})
        queries = [q.strip() for q in result.split('\n') if q.strip()]
        self.stats["mqe_queries_generated"] += len(queries)
        return queries
    
    def _generate_hyde_hypothesis(self, question: str) -> str:
        """生成假设文档"""
        prompt = ChatPromptTemplate.from_template(
            "请针对以下问题，撰写一个假设性的标准答案片段:\n\n问题：{question}\n\n假设答案:"
        )
        chain = prompt | self.llm | StrOutputParser()
        hypothesis = chain.invoke({"question": question})
        self.stats["hyde_hypotheses_generated"] += 1
        return hypothesis
    
    def _retrieve_with_mqe_and_hyde(self, question: str) -> List:
        """MQE + HyDE 组合检索"""
        # MQE 分支
        mqe_queries = self._generate_mqe_queries(question)
        mqe_docs = []
        for query in mqe_queries:
            docs = self.retriever.invoke(query)
            mqe_docs.extend(docs)
        
        # HyDE 分支
        hypothesis = self._generate_hyde_hypothesis(question)
        hyde_docs = self.retriever.invoke(hypothesis)
        
        # 融合多源结果
        fused_docs = self._fuse_multi_source_context([mqe_docs, hyde_docs])
        return fused_docs
    
    def _retrieve_with_mqe(self, question: str) -> List:
        """只使用 MQE 检索"""
        queries = self._generate_mqe_queries(question)
        all_docs = []
        for query in queries:
            docs = self.retriever.invoke(query)
            all_docs.extend(docs)
        return all_docs
    
    def _retrieve_with_hyde(self, question: str) -> List:
        """只使用 HyDE 检索"""
        hypothesis = self._generate_hyde_hypothesis(question)
        return self.retriever.invoke(hypothesis)
    
    def _basic_retrieve(self, question: str) -> List:
        """基础检索"""
        return self.retriever.invoke(question)
    
    # ==================== 上下文工程核心功能 ====================
    
    def _initialize_context_compressor(self):
        """初始化上下文压缩器（简化版）"""
        try:
            print(f"  ✓ 上下文压缩器已初始化 (基于规则的智能压缩)")
        except Exception as e:
            print(f"  ⚠️ 上下文压缩器初始化失败：{e}")
    
    def _compress_context(self, question: str, documents: List) -> List:
        """上下文压缩：提取与问题最相关的信息"""
        if not documents:
            return documents
        
        try:
            # 计算每个文档的相关性分数
            scored_docs = []
            for doc in documents:
                similarity = self._calculate_similarity(question, doc.page_content)
                score = similarity * (1.0 / (1.0 + len(doc.page_content) / 1000))
                scored_docs.append((doc, score))
            
            # 按分数降序排序
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # 只保留 top 5 个最相关的文档
            compressed_docs = [doc for doc, _ in scored_docs[:5]]
            
            self.stats["context_compressed"] += 1
            
            original_length = sum(len(doc.page_content) for doc in documents)
            compressed_length = sum(len(doc.page_content) for doc in compressed_docs)
            compression_ratio = (original_length - compressed_length) / original_length if original_length > 0 else 0
            
            print(f"  📦 上下文压缩：{len(documents)} → {len(compressed_docs)} 个文档")
            print(f"     压缩率：{compression_ratio:.1%}")
            
            return compressed_docs
        except Exception as e:
            print(f"  ⚠️ 上下文压缩失败：{e}")
            return documents
    
    def _rank_context_by_relevance(self, question: str, documents: List) -> List:
        """上下文排序：根据相关性排序"""
        if not documents:
            return documents
        
        try:
            scored_docs = []
            for doc in documents:
                similarity = self._calculate_similarity(question, doc.page_content)
                scored_docs.append((doc, similarity))
            
            # 按相似度降序排列
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # 过滤低质量文档
            filtered_docs = [doc for doc, score in scored_docs if score >= self.context_quality_threshold]
            
            if not filtered_docs and scored_docs:
                filtered_docs = [scored_docs[0][0]]
            
            print(f"  📊 上下文排序：{len(documents)} → {len(filtered_docs)} 个高质量文档")
            
            return filtered_docs
        except Exception as e:
            print(f"  ⚠️ 上下文排序失败：{e}")
            return documents
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算余弦相似度"""
        try:
            embedding1 = self.embeddings.embed_query(text1)
            embedding2 = self.embeddings.embed_query(text2)
            
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
            norm1 = sum(a * a for a in embedding1) ** 0.5
            norm2 = sum(b * b for b in embedding2) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            self.stats["context_quality_scores"].append(similarity)
            
            return similarity
        except Exception as e:
            print(f"  ⚠️ 相似度计算失败：{e}")
            return 0.0
    
    def _adapt_context_window(self, question: str, documents: List) -> List:
        """动态上下文窗口：根据输入长度调整"""
        if not documents:
            return documents
        
        try:
            total_length = sum(len(doc.page_content) for doc in documents)
            
            if total_length > self.max_context_length:
                print(f"  🔧 上下文过长 ({total_length} > {self.max_context_length})，自适应调整...")
                
                ranked_docs = self._rank_context_by_relevance(question, documents)
                
                accumulated_length = 0
                selected_docs = []
                
                for doc in ranked_docs:
                    if accumulated_length + len(doc.page_content) <= self.max_context_length:
                        selected_docs.append(doc)
                        accumulated_length += len(doc.page_content)
                    else:
                        break
                
                print(f"  📏 窗口调整：保留 {len(selected_docs)} 个文档")
                return selected_docs
            
            return documents
        except Exception as e:
            print(f"  ⚠️ 窗口调整失败：{e}")
            return documents
    
    def _evaluate_context_quality(self, question: str, documents: List) -> Dict[str, Any]:
        """上下文质量评估"""
        if not documents:
            return {"quality_score": 0.0, "metrics": {}}
        
        try:
            similarities = []
            for doc in documents:
                sim = self._calculate_similarity(question, doc.page_content)
                similarities.append(sim)
            
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
            max_similarity = max(similarities) if similarities else 0.0
            min_similarity = min(similarities) if similarities else 0.0
            
            lengths = [len(doc.page_content) for doc in documents]
            length_variance = sum((l - sum(lengths)/len(lengths))**2 for l in lengths) / len(lengths) if lengths else 0
            diversity_score = min(1.0, length_variance / 1000)
            
            quality_score = (
                avg_similarity * 0.6 +
                max_similarity * 0.3 +
                diversity_score * 0.1
            )
            
            quality_report = {
                "quality_score": round(quality_score, 3),
                "metrics": {
                    "avg_similarity": round(avg_similarity, 3),
                    "max_similarity": round(max_similarity, 3),
                    "min_similarity": round(min_similarity, 3),
                    "num_documents": len(documents),
                    "total_length": sum(lengths),
                    "diversity_score": round(diversity_score, 3)
                }
            }
            
            print(f"  📈 上下文质量：{quality_report['quality_score']:.2f}/1.00")
            return quality_report
        except Exception as e:
            print(f"  ⚠️ 质量评估失败：{e}")
            return {"quality_score": 0.0, "metrics": {}}
    
    def _fuse_multi_source_context(self, sources: List[List]) -> List:
        """上下文融合：整合多源检索结果"""
        if not sources:
            return []
        
        try:
            all_docs = []
            for source in sources:
                all_docs.extend(source)
            
            seen = set()
            unique_docs = []
            for doc in all_docs:
                content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
                if content_hash not in seen:
                    seen.add(content_hash)
                    unique_docs.append(doc)
            
            print(f"  🔀 上下文融合：{sum(len(s) for s in sources)} → {len(unique_docs)} 个唯一文档")
            
            return unique_docs
        except Exception as e:
            print(f"  ⚠️ 上下文融合失败：{e}")
            return []
    
    def _record_retrieval_to_memory(self, question: str, answer: str, sources: List, retrieval_method: str):
        """记录检索过程到记忆系统"""
        # 1. 情景记忆：记录 QA 事件
        self.memory_manager.add_episodic_memory(
            event_type="query_answer",
            query=question,
            response=answer,
            sources=[s["source"] for s in sources],
            tags=["qa", retrieval_method]
        )
        
        # 2. 语义记忆：提取关键概念
        concept_keywords = self._extract_concepts(answer)
        for concept in concept_keywords[:3]:
            self.memory_manager.add_semantic_memory(
                concept=concept,
                definition=answer[:200],
                category="qa_derived"
            )
        
        # 3. 更新工作记忆（如果存在）
        task_id = f"query_{datetime.now().strftime('%H%M%S')}"
        if hasattr(self.memory_manager, 'working_memories'):
            working_memory = self.memory_manager.working_memories.get(task_id)
            if working_memory:
                working_memory.add_context(f"Q: {question}")
                working_memory.add_context(f"A: {answer[:100]}...")
        
        self.stats["memories_created"] += 4
    
    def _extract_concepts(self, text: str) -> List[str]:
        """从文本中提取关键概念"""
        prompt = ChatPromptTemplate.from_template(
            "从以下文本中提取 3-5 个关键概念或术语，用逗号分隔:\n\n{text}\n\n关键概念:"
        )
        chain = prompt | self.llm | StrOutputParser()
        result = chain.invoke({"text": text})
        concepts = [c.strip() for c in result.split(',') if c.strip()]
        return concepts


# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    import json
    
    print("=" * 80)
    print("🚀 CodeMind Assistant - 代码库智能维护助手")
    print("   整合文档问答 + 代码探索 + 任务管理 + 长程记忆")
    print("=" * 80)
    
    # 创建助手实例
    assistant = CodeMindAssistant(
        user_id="demo_user",
        project_path=str(Path.cwd())
    )
    
    # 场景 1: 加载文档并问答
    pdf_path = "Happy-LLM-0727.pdf"
    if not os.path.exists(pdf_path):
        pdf_path = "CodeMind/Happy-LLM-0727.pdf"
    
    if os.path.exists(pdf_path):
        print(f"\n📄 加载文档：{pdf_path}")
        assistant.load_document(pdf_path)
        
        # 测试问答
        test_questions = [
            "这篇文档主要讲了什么内容？",
            "有哪些关键概念？",
            "能总结一下核心观点吗？"
        ]
        
        print("\n" + "=" * 80)
        print("🤔 问答测试")
        print("=" * 80)
        
        for i, q in enumerate(test_questions, 1):
            print(f"\n【问题{i}】{q}")
            result = assistant.ask(q, use_mqe=True, use_hyde=True)
            print(f"【回答】{result['answer'][:300]}...")
            print(f"【检索方法】{result['retrieval_method']}")
            print(f"【来源数量】{result['num_sources']} 个文档片段")
    
    # 场景 2: 探索代码库
    print("\n" + "=" * 80)
    print("💻 代码库探索")
    print("=" * 80)
    
    assistant.explore_codebase("ls -la")
    assistant.explore_codebase("find . -name '*.py' -type f | head -20")
    
    # 场景 3: 分析文件
    print("\n" + "=" * 80)
    print("🔍 文件分析")
    print("=" * 80)
    
    file_analysis = assistant.analyze_file("codemind_assistant.py")
    print(f"文件行数：{file_analysis['stats'].get('lines', -1)}")
    
    # 场景 4: 搜索代码
    print("\n" + "=" * 80)
    print("🔎 代码搜索")
    print("=" * 80)
    
    search_result = assistant.search_in_codebase("class.*Assistant", "*.py")
    print(f"搜索结果预览：{search_result[:500]}...")
    
    # 场景 5: 创建任务
    print("\n" + "=" * 80)
    print("✅ 任务管理")
    print("=" * 80)
    
    task_id = assistant.create_task(
        title="重构代码结构",
        description="优化 codemind_assistant.py 的模块组织",
        priority="high",
        tags=["refactor", "code_quality"],
        related_files=["codemind_assistant.py"]
    )
    print(f"创建任务 ID: {task_id}")
    
    # 查看任务摘要
    task_summary = assistant.get_task_summary()
    print(f"\n任务摘要:")
    print(f"  - 总笔记数：{task_summary['total_notes']}")
    print(f"  - 待处理问题：{task_summary['open_issues']}")
    print(f"  - 进行中任务：{task_summary['pending_tasks']}")
    
    # 生成学习报告
    print("\n" + "=" * 80)
    print("📊 生成学习报告")
    print("=" * 80)
    
    report = assistant.generate_learning_report("codemind_report.json")
    print(f"\n报告统计:")
    print(f"  - 加载文档：{report['rag_statistics']['documents_loaded']}")
    print(f"  - 回答问题：{report['rag_statistics']['questions_asked']}")
    print(f"  - 创建笔记：{report['notes']['total_notes']}")
    print(f"  - 执行命令：{report['terminal']['total_commands']}")
    
    # 获取完整统计
    stats = assistant.get_stats()
    print(f"\n完整统计:")
    print(f"  - 会话时长：{stats['session_duration']}")
    print(f"  - 总记忆数：{stats['total_memories']}")
    print(f"  - 上下文质量：{stats['context_engineering']['avg_context_quality']:.3f}")
    
    print("\n" + "=" * 80)
    print("✅ CodeMind Assistant 演示完成！")
    print("=" * 80)