"""
基于 LangChain 的智能文档问答助手
支持 PDF/TXT 文档加载、向量存储检索 (RAG)、对话记忆管理
"""

import os
import dotenv
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# 加载环境变量
dotenv.load_dotenv()


class PDFLearningAssistant:
    """基于 LangChain 的智能文档问答助手"""

    def __init__(self, user_id: str = "default_user"):
        """初始化学习助手

        Args:
            user_id: 用户 ID，用于隔离不同用户的数据
        """
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
        
        # 文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""],
        )
        
        # 对话历史 - 手动管理
        self.chat_history: List[str] = []
        
        # 向量存储（初始化为 None，加载文档后创建）
        self.vectorstore: Optional[FAISS] = None
        
        # 检索器
        self.retriever = None
        
        # 学习统计
        self.stats = {
            "session_start": datetime.now(),
            "documents_loaded": 0,
            "questions_asked": 0,
            "chunks_created": 0
        }
        
        # 当前加载的文档路径
        self.current_document_paths: List[str] = []

    def load_document(self, file_path: str) -> bool:
        """加载文档到向量存储

        Args:
            file_path: PDF 或 TXT 文件路径

        Returns:
            是否加载成功
        """
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"错误：文件不存在 - {file_path}")
                return False
            
            # 根据文件类型选择加载器
            if path.suffix.lower() == '.pdf':
                loader = PyPDFLoader(str(path))
            elif path.suffix.lower() == '.txt':
                loader = TextLoader(str(path), encoding='utf-8')
            else:
                print(f"不支持的文件类型：{path.suffix}")
                return False
            
            # 加载文档
            documents = loader.load()
            
            # 添加元数据
            for doc in documents:
                doc.metadata["source"] = str(path)
                doc.metadata["user_id"] = self.user_id
            
            # 分割文本
            chunks = self.text_splitter.split_documents(documents)
            
            # 创建或更新向量存储
            if self.vectorstore is None:
                self.vectorstore = FAISS.from_documents(chunks, self.embeddings)
            else:
                self.vectorstore.add_documents(chunks)
            
            # 创建检索器
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 3}  # 返回最相关的 3 个文档片段
            )
            
            # 更新统计
            self.stats["documents_loaded"] += 1
            self.stats["chunks_created"] += len(chunks)
            self.current_document_paths.append(str(path))
            
            print(f"✓ 成功加载文档：{path.name}")
            print(f"  - 文本块数量：{len(chunks)}")
            print(f"  - 累计文档数：{self.stats['documents_loaded']}")
            
            return True
            
        except Exception as e:
            print(f"加载文档失败：{e}")
            return False

    def _format_docs(self, docs):
        """格式化文档为字符串"""
        return "\n\n".join(doc.page_content for doc in docs)

    def ask(self, question: str) -> dict:
        """提问并获取回答

        Args:
            question: 问题内容

        Returns:
            包含回答和源文档的字典
        """
        if self.vectorstore is None or self.retriever is None:
            return {
                "answer": "请先加载文档后再提问。",
                "sources": []
            }
        
        try:
            # 创建提示模板
            template = """使用以下上下文片段来回答问题。如果不知道答案，就说你不知道，不要编造答案。尽量给出详细和准确的回答。

上下文信息:
{context}

问题：{question}
有用回答:"""
            
            prompt = ChatPromptTemplate.from_template(template)
            
            # 创建 RAG 链
            rag_chain = (
                {"context": self.retriever | self._format_docs, "question": RunnablePassthrough()}
                | prompt
                | self.llm
                | StrOutputParser()
            )
            
            # 执行问答
            answer = rag_chain.invoke(question)
            
            # 更新统计
            self.stats["questions_asked"] += 1
            
            # 提取源文档信息
            docs = self.retriever.invoke(question)
            sources = []
            for doc in docs:
                sources.append({
                    "content": doc.page_content[:200] + "...",
                    "source": doc.metadata.get("source", "unknown"),
                    "page": doc.metadata.get("page", 0)
                })
            
            response = {
                "answer": answer,
                "sources": sources,
                "question": question
            }
            
            return response
            
        except Exception as e:
            return {
                "answer": f"回答问题时出错：{e}",
                "sources": []
            }

    def get_stats(self) -> dict:
        """获取学习统计信息"""
        return {
            **self.stats,
            "session_duration": datetime.now() - self.stats["session_start"],
            "loaded_files": [Path(p).name for p in self.current_document_paths]
        }

    def reset(self):
        """重置助手状态"""
        self.vectorstore = None
        self.retriever = None
        self.chat_history = []
        self.current_document_paths = []
        self.stats = {
            "session_start": datetime.now(),
            "documents_loaded": 0,
            "questions_asked": 0,
            "chunks_created": 0
        }
        print("✓ 助手已重置")


# 使用示例
if __name__ == "__main__":
    print("=" * 60)
    print("LangChain 智能文档问答助手")
    print("=" * 60)
    
    # 创建助手实例
    assistant = PDFLearningAssistant(user_id="user_001")
    
    # 加载文档（PDF 文件在 01_hello_agent 目录下）
    pdf_path = "Happy-LLM-0727.pdf"  # 相对路径，文件在当前运行目录的子目录下
    # 尝试两种可能的路径
    if not os.path.exists(pdf_path):
        pdf_path = "01_hello_agent/Happy-LLM-0727.pdf"  # 从项目根目录运行时的路径
    
    if os.path.exists(pdf_path):
        assistant.load_document(pdf_path)
        
        # 提问
        questions = [
            "这篇文档主要讲了什么内容？",
            "有哪些关键概念？",
            "能总结一下核心观点吗？"
        ]
        
        for q in questions:
            print(f"\n问：{q}")
            result = assistant.ask(q)
            print(f"答：{result['answer']}")
            if result['sources']:
                print(f"来源：{len(result['sources'])} 个文档片段")
    else:
        print(f"\n提示：请将 '{pdf_path}' 替换为实际的 PDF 文件路径")
        print("\n使用步骤:")
        print("1. 准备一个 PDF 或 TXT 文件")
        print("2. 修改 pdf_path 变量指向该文件")
        print("3. 运行程序进行问答")
        print("\n示例代码:")
        print('   pdf_path = "docs/my_document.pdf"')
        print("   assistant.load_document(pdf_path)")
        print('   result = assistant.ask("文档的主要内容是什么？")')
