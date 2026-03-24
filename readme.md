# 🚀 CodeMind - 智能代码助手

基于 LangChain + RAG 的智能代码问答助手，支持多工作空间管理和上下文工程。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-green.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.100+-lightgrey.svg)

## 📌 快速导航

- **📖 完整文档**: [docs/INDEX.md](docs/INDEX.md)
- **⚡ 快速开始**: [docs/QUICKSTART.md](docs/QUICKSTART.md)
- **💻 开发指南**: [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md)
- **🗄️ 数据库架构**: [docs/DATABASE_GUIDE.md](docs/DATABASE_GUIDE.md)
- **🔌 API 参考**: [docs/API_GUIDE.md](docs/API_GUIDE.md)

---

## ✨ 核心特性

### 🧠 智能代码问答
- 基于 RAG 的混合检索（向量相似度 + SQL 过滤）
- 支持 PDF、Word、Excel、PPT、Markdown、Python 等格式
- 自动分块和向量化处理

### 📁 多工作空间管理
- 每个工作空间独立的知识库
- 工作空间切换和隔离
- 支持短 ID（8 位）和完整 UUID（36 位）

### 🔍 上下文工程
- 多层次记忆系统（会话历史、笔记、任务）
- 智能路由和查询优化
- Hyde 和多查询扩展

### 🔧 MCP 集成
- Model Context Protocol 支持
- 可扩展的工具和服务器
- 标准化的外部服务集成

### 💾 持久化存储
- PostgreSQL：文档元数据、用户信息、操作日志
- Milvus：向量数据存储
- FAISS：本地缓存（可选）

## 🚀 快速开始

### 环境要求

- Python 3.10+
- PostgreSQL 15+ (带 pgvector 扩展)
- Milvus 向量数据库
- Docker & Docker Compose (可选，用于快速部署)

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd helloagentlearning
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
# 复制环境变量模板
cp 01_hello_agent/.env.example 01_hello_agent/.env

# 编辑 .env 文件，配置 LLM API
OPENAI_API_KEY=your_api_key
MODEL=gpt-4o-mini
BASE_URL=https://api.openai-proxy.org/v1
```

4. **启动数据库服务**
```bash
# 使用 Docker Compose (推荐)
cd 01_hello_agent
docker-compose up -d

# 或者手动启动 PostgreSQL 和 Milvus
```

5. **初始化数据库**
```bash
cd 01_hello_agent
python init_database.py
```

6. **启动 Web 应用**
```bash
# Windows
.\start_docker.ps1

# Linux/Mac
./start_docker_wsl.sh

# 或直接运行
python start_web_app.py
```

7. **访问应用**
打开浏览器访问：http://localhost:8000

## ✨ 核心功能

### 1. 智能代码问答
- 基于 RAG 的混合检索（向量相似度 + SQL 过滤）
- 支持多种文件格式：PDF, Word, Excel, PPT, TXT, Markdown, Python 等
- 自动分块和向量化处理

### 2. 多工作空间管理
- 每个工作空间独立的知识库
- 工作空间切换和隔离
- 支持短 ID（8 位）和完整 UUID（36 位）两种模式

### 3. 上下文工程
- 多层次记忆系统（会话历史、笔记、任务）
- 智能路由和查询优化
- Hyde（假设文档嵌入）和多查询扩展

### 4. MCP 集成
- Model Context Protocol 支持
- 可扩展的工具和服务器
- 标准化的外部服务集成

### 5. 持久化存储
- PostgreSQL：文档元数据、用户信息、操作日志
- Milvus：向量数据存储
- FAISS：本地缓存（可选）

## 📁 项目结构

```
helloagentlearning/
├── 01_hello_agent/          # 主应用目录
│   ├── core/                # 核心逻辑
│   │   ├── codemind_assistant_db.py    # 数据库增强版助手
│   │   ├── context_builder.py          # 上下文构建器
│   │   └── memory_system.py            # 记忆系统
│   ├── database/            # 数据库相关
│   │   ├── models.py                   # ORM 模型
│   │   ├── dao.py                      # 数据访问对象
│   │   ├── db_connection.py            # 数据库连接
│   │   └── milvus_client.py            # Milvus 客户端
│   ├── web_app/             # Web 应用
│   │   ├── web_api.py                  # FastAPI 路由
│   │   └── static/                     # 静态文件
│   ├── tools/               # 工具集
│   │   ├── mcp_server.py               # MCP 服务器
│   │   ├── pdf_assistant.py            # PDF 处理
│   │   └── terminal_tool.py            # 终端工具
│   ├── tests/               # 测试用例
│   ├── workspaces/          # 工作空间数据（运行时生成）
│   ├── docker-compose.yml   # Docker 配置
│   ├── init_database.py     # 数据库初始化
│   └── start_web_app.py     # Web 应用入口
├── docs/                    # 项目文档
├── requirements.txt         # Python 依赖
└── README.md               # 本文件
```

## 🏗️ 技术架构

### 后端技术栈
- **FastAPI**: Web 框架
- **LangChain**: LLM 应用开发框架
- **SQLAlchemy**: ORM 工具
- **MarkItDown**: 文档解析工具

### 数据库
- **PostgreSQL 15+**: 关系型数据库（带 pgvector 扩展）
- **Milvus**: 向量数据库
- **FAISS**: 本地向量索引（可选）

### 架构特点
1. **双存储引擎**: PostgreSQL + Milvus 混合架构
2. **多级缓存**: 内存 → FAISS → Milvus
3. **工作空间隔离**: 每个工作空间独立的向量集合
4. **外键约束**: 严格的数据完整性保证

## 📖 使用指南

### 创建工作空间
1. 点击"创建工作空间"按钮
2. 输入名称和描述
3. 自动切换到新工作空间

### 上传文档
1. 选择活跃的工作空间
2. 拖拽或点击上传文件
3. 系统自动处理并索引文档

### 智能问答
1. 在对话框输入问题
2. 系统自动检索相关上下文
3. 返回准确的答案和来源

### 管理笔记
1. 创建任务、决策、问题笔记
2. 关联到特定工作空间
3. 跟踪进度和状态

## ❓ 常见问题

### Q: 上传文件时报外键约束错误？
**A**: 确保工作空间已正确创建并切换到该工作空间。系统会自动在数据库中同步工作空间信息。

### Q: 如何查看已上传的文档？
**A**: 在工作空间页面会显示所有文档列表，包括文件名、大小和状态。

### Q: 支持哪些文件格式？
**A**: 支持 PDF、Word (.docx)、Excel (.xlsx)、PPT (.pptx)、TXT、Markdown、Python 代码等主流格式。

### Q: 如何切换工作空间？
**A**: 在工作空间列表中选择目标工作空间，点击切换即可。

### Q: 向量数据库是必须的吗？
**A**: 是的，Milvus 用于存储向量数据。可以使用 Docker Compose 快速部署。

## 🔧 开发指南

### 运行测试
```bash
cd 01_hello_agent/tests
python test_web_api.py
```

### 添加新的 MCP 工具
参考 `tools/mcp_server.py` 的实现。

### 自定义文档处理流程
修改 `core/codemind_assistant_db.py` 中的 `upload_document` 方法。

## 📝 更新日志

### v2.0 - 数据库增强版
- ✅ 引入 PostgreSQL + Milvus 双存储
- ✅ 修复工作空间同步问题
- ✅ 优化文件上传流程
- ✅ 改进外键约束处理

### v1.0 - 初始版本
- ✅ 基础 RAG 功能
- ✅ FAISS 向量存储
- ✅ Web 界面

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
