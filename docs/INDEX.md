# CodeMind 项目文档索引

欢迎使用 CodeMind 智能代码助手！本文档索引帮助你快速找到所需信息。

## 📚 文档导航

### 🚀 新手入门

1. **[README.md](../README.md)** - 项目总览和快速开始
   - 核心功能介绍
   - 技术架构概览
   - 快速安装指南

2. **[docs/QUICKSTART.md](QUICKSTART.md)** - 详细的环境搭建指南
   - Docker Compose 部署（推荐）
   - 本地安装部署
   - 测试和验证
   - 常见问题排查

### 💻 开发指南

3. **[docs/DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)** - 开发者必读
   - 开发环境配置
   - 代码结构详解
   - 核心流程解析
   - 扩展指南
   - 测试指南
   - 性能优化建议

4. **[docs/DATABASE_GUIDE.md](DATABASE_GUIDE.md)** - 数据库架构详解
   - 双存储引擎设计
   - 表结构说明
   - Milvus 集合设计
   - 数据访问层 (DAO)
   - 性能优化技巧
   - 故障排查

5. **[docs/API_GUIDE.md](API_GUIDE.md)** - API 接口文档
   - 工作空间管理 API
   - 文件上传 API
   - 智能问答 API
   - 会话管理 API
   - MCP 集成 API
   - 使用示例

### 📖 专项主题

6. **MCP 集成** 
   - 参考 `01_hello_agent/tools/mcp_server.py`
   - 如何添加自定义 MCP 工具

7. **上下文工程**
   - 参考 `01_hello_agent/core/context_builder.py`
   - 多层次记忆系统实现

8. **向量检索优化**
   - 参考 `01_hello_agent/database/dao.py` 中的 `RetrieverService`
   - 混合检索策略实现

## 🗂️ 项目文件结构

```
helloagentlearning/
├── README.md                    # 项目总览 ⭐
├── requirements.txt             # Python 依赖
├── .gitignore                   # Git 忽略文件
│
├── docs/                        # 项目文档 📚
│   ├── QUICKSTART.md           # 快速开始指南
│   ├── DEVELOPMENT_GUIDE.md    # 开发指南
│   ├── DATABASE_GUIDE.md       # 数据库指南
│   └── API_GUIDE.md            # API 文档
│
├── 01_hello_agent/              # 主应用目录
│   ├── core/                   # 核心业务逻辑
│   │   ├── codemind_assistant.py
│   │   ├── codemind_assistant_db.py  ⭐ 主要助手类
│   │   ├── context_builder.py
│   │   └── memory_system.py
│   │
│   ├── database/               # 数据访问层
│   │   ├── models.py           # ORM 模型
│   │   ├── dao.py              # DAO 实现
│   │   ├── db_connection.py    # 数据库连接
│   │   └── milvus_client.py    # Milvus 客户端
│   │
│   ├── web_app/                # Web 应用
│   │   ├── web_api.py          # FastAPI 路由
│   │   └── static/             # 前端文件
│   │
│   ├── tools/                  # 工具集
│   │   ├── mcp_server.py
│   │   ├── pdf_assistant.py
│   │   └── terminal_tool.py
│   │
│   ├── tests/                  # 测试用例
│   ├── examples/               # 示例代码
│   ├── docker-compose.yml      # Docker 配置
│   └── init_database.py        # 数据库初始化
│
└── workspaces/                 # 工作空间数据（运行时生成）
    └── {workspace_id}/
        ├── documents/          # 上传的文档
        ├── sessions/           # 会话历史
        └── vectorstore/        # 向量存储
```

## 🎯 按主题查找

### 安装和部署
- 环境要求 → [README.md](../README.md#快速开始)
- Docker 部署 → [QUICKSTART.md](QUICKSTART.md#方式一使用-docker-compose)
- 本地部署 → [QUICKSTART.md](QUICKSTART.md#方式二本地安装数据库)
- 故障排查 → [QUICKSTART.md](QUICKSTART.md#常见问题)

### 使用指南
- 创建工作空间 → [API_GUIDE.md](API_GUIDE.md#1-创建工作空间)
- 上传文档 → [API_GUIDE.md](API_GUIDE.md#5-上传文件)
- 智能问答 → [API_GUIDE.md](API_GUIDE.md#8-发送问题)
- 管理笔记 → [API_GUIDE.md](API_GUIDE.md#笔记管理-api)

### 开发相关
- 代码结构 → [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md#代码结构详解)
- 核心流程 → [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md#核心流程解析)
- 添加新功能 → [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md#扩展指南)
- 编写测试 → [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md#测试指南)

### 数据库
- 表结构 → [DATABASE_GUIDE.md](DATABASE_GUIDE.md#数据库表结构)
- 向量集合 → [DATABASE_GUIDE.md](DATABASE_GUIDE.md#milvus-向量集合)
- 数据访问 → [DATABASE_GUIDE.md](DATABASE_GUIDE.md#数据访问层-dao)
- 性能优化 → [DATABASE_GUIDE.md](DATABASE_GUIDE.md#性能优化建议)

### API 参考
- REST API → [API_GUIDE.md](API_GUIDE.md)
- WebSocket → [API_GUIDE.md](API_GUIDE.md#websocket-实时通信)
- MCP 工具 → [API_GUIDE.md](API_GUIDE.md#mcp-model-context-protocol-api)

## 🔧 快速参考

### 常用命令

```bash
# 启动数据库服务
cd 01_hello_agent
docker-compose up -d

# 初始化数据库
python init_database.py

# 启动 Web 应用
python start_web_app.py

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 重要配置文件

- `.env` - 环境变量配置
- `docker-compose.yml` - Docker 服务配置
- `requirements.txt` - Python 依赖

### 关键代码文件

| 文件 | 用途 | 重要性 |
|------|------|--------|
| `core/codemind_assistant_db.py` | 主要助手类，整合所有功能 | ⭐⭐⭐ |
| `web_app/web_api.py` | Web API 路由和业务逻辑 | ⭐⭐⭐ |
| `database/models.py` | 数据库 ORM 模型 | ⭐⭐ |
| `database/dao.py` | 数据访问操作 | ⭐⭐ |
| `database/milvus_client.py` | Milvus 向量数据库操作 | ⭐⭐ |

## 📞 获取帮助

### 文档未解答的问题？

1. **查看源代码注释** - 代码中有详细的文档字符串
2. **检查示例代码** - `examples/` 目录提供使用示例
3. **运行测试** - `tests/` 目录展示各种用法

### 遇到问题？

1. **常见问题** → [QUICKSTART.md](QUICKSTART.md#常见问题)
2. **数据库问题** → [DATABASE_GUIDE.md](DATABASE_GUIDE.md#常见问题排查)
3. **API 错误** → [API_GUIDE.md](API_GUIDE.md#错误处理)

### 仍然无法解决？

- 提交 Issue 到项目仓库
- 查看项目的 Discussions
- 联系维护者

## 🎓 学习路径

### 初学者路径

1. 阅读 [README.md](../README.md) 了解项目
2. 按照 [QUICKSTART.md](QUICKSTART.md) 搭建环境
3. 使用 Web 界面体验基本功能
4. 阅读 [API_GUIDE.md](API_GUIDE.md) 学习 API 调用

### 开发者路径

1. 完成初学者路径
2. 深入学习 [DEVELOPMENT_GUIDE.md](DEVELOPMENT_GUIDE.md)
3. 研究 [DATABASE_GUIDE.md](DATABASE_GUIDE.md) 了解架构
4. 阅读核心源码：`codemind_assistant_db.py`
5. 尝试添加新功能或修复 Bug

### 高级用户路径

1. 理解整体架构
2. 优化性能参数
3. 自定义文档处理流程
4. 开发专属 MCP 工具
5. 贡献代码到项目

## 📝 文档更新记录

- **2024-03-24**: 重构文档结构，新增四大核心文档
  - README.md: 项目总览
  - QUICKSTART.md: 快速开始
  - DEVELOPMENT_GUIDE.md: 开发指南
  - DATABASE_GUIDE.md: 数据库指南
  - API_GUIDE.md: API 文档

- **之前版本**: 分散的 Markdown 文件
  - CODEMIND_SUMMARY.md (已删除)
  - CONTEXT_ENGINEERING_SUMMARY.md (已删除)
  - DEVELOPMENT_REPORT.md (已删除)
  - DATABASE_SETUP_GUIDE.md (已删除)

---

**祝你使用愉快！** 🚀

如有任何问题或建议，欢迎反馈！
