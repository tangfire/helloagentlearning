# 🚀 CodeMind Assistant - MCP 集成指南

## 📋 什么是 MCP？

**MCP (Model Context Protocol)** 是一个标准化协议，允许 AI模型与外部工具和服务进行安全、结构化的交互。它就像是 AI 的"USB 接口"，可以即插即用各种功能模块。

---

## 🎯 CodeMind 的 MCP 能力

### 1️⃣ **作为 MCP Server** - 对外提供服务

CodeMind Assistant 可以作为 MCP 服务器运行，向其他 AI 助手（如 Claude）提供以下能力：

#### 🔧 可用工具（10 个）

| 工具名称 | 功能描述 |
|---------|---------|
| `explore_codebase` | 探索代码库结构（支持 dir, find, tree 等命令） |
| `analyze_file` | 分析文件结构和内容（统计、预览、结构） |
| `search_in_codebase` | 在代码库中搜索模式（正则表达式） |
| `ask_question` | 基于文档和代码的智能问答 |
| `create_task` | 创建任务或记录问题 |
| `list_tasks` | 列出任务/笔记 |
| `update_task_status` | 更新任务状态或内容 |
| `load_document` | 加载文档到知识库 |
| `get_context` | 获取与查询相关的历史上下文 |
| `get_project_stats` | 获取项目统计信息 |

#### 📚 可用资源（2 个）

- `codemind://tasks/{task_id}` - 获取特定任务的详细信息
- `codemind://files/{filepath}` - 获取文件内容

#### 💬 提示词模板（2 个）

- `code_review_prompt` - 代码审查提示词
- `refactoring_plan_prompt` - 重构计划提示词

---

### 2️⃣ **作为 MCP Client** - 连接外部服务

CodeMind 可以连接外部 MCP 服务，扩展自身能力：

#### 可连接的服务示例

```python
# 文件系统服务
assistant.connect_to_mcp_server(
    "filesystem",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/project"]
)

# Git 版本控制服务
assistant.connect_to_mcp_server(
    "git",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-git"]
)

# 数据库服务
assistant.connect_to_mcp_server(
    "database",
    command="python",
    args=["-m", "mcp_server_database"]
)
```

#### 调用外部工具

```python
# 异步调用 MCP 工具
result = await assistant.call_mcp_tool(
    server_name="filesystem",
    tool_name="read_directory",
    arguments={"path": "/path/to/dir"}
)
```

---

## 🛠️ 使用方法

### 方式 1: 作为独立 MCP Server 运行

```bash
# 方法 1: 直接运行
python mcp_server.py

# 方法 2: 使用 MCP CLI
mcp dev mcp_server.py

# 方法 3: HTTP 模式
mcp serve mcp_server.py --transport http
```

### 方式 2: 在 Claude Desktop 中使用

配置 Claude Desktop 连接到 CodeMind MCP Server：

1. 打开 Claude Desktop 配置文件
2. 添加 MCP server 配置：

```json
{
  "mcpServers": {
    "codemind": {
      "command": "python",
      "args": ["D:\\GitRespority\\helloagentlearning\\01_hello_agent\\mcp_server.py"],
      "cwd": "D:\\GitRespority\\helloagentlearning\\01_hello_agent"
    }
  }
}
```

3. 重启 Claude Desktop
4. 现在可以直接使用 CodeMind 的所有功能！

### 方式 3: 在 CodeMind 中使用外部 MCP 服务

```python
from codemind_assistant import CodeMindAssistant

# 创建助手实例
assistant = CodeMindAssistant(user_id="my_user")

# 连接外部 MCP 服务
assistant.connect_to_mcp_server(
    "filesystem",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem"]
)

# 查看 MCP 状态
status = assistant.get_mcp_status()
print(f"已连接 {status['connected_servers']} 个 MCP 服务器")

# 调用外部工具（需要异步）
import asyncio

async def use_external_tool():
    result = await assistant.call_mcp_tool(
        "filesystem",
        "read_file",
        {"path": "readme.md"}
    )
    print(f"文件内容：{result}")

asyncio.run(use_external_tool())
```

---

## 📊 完整工作流示例

### 场景：代码库维护

```python
from codemind_assistant import CodeMindAssistant
import asyncio

# 1. 创建助手
assistant = CodeMindAssistant(project_path="/path/to/project")

# 2. 探索代码库（本地工具）
result = assistant.explore_codebase("dir")

# 3. 连接外部 Git 服务（MCP Client）
assistant.connect_to_mcp_server(
    "git",
    command="npx",
    args=["-y", "@modelcontextprotocol/server-git"]
)

# 4. 分析文件（本地工具）
file_info = assistant.analyze_file("main.py")

# 5. 发现问题，创建任务（本地工具）
task_id = assistant.create_task(
    title="优化 main.py 性能",
    description="发现复杂度过高，需要重构",
    priority="high",
    tags=["refactor", "performance"]
)

# 6. 调用 Git 工具提交更改（MCP 工具）
async def commit_changes():
    await assistant.call_mcp_tool(
        "git",
        "git_commit",
        {
            "message": "优化 main.py 性能",
            "files": ["main.py"]
        }
    )

asyncio.run(commit_changes())

# 7. 生成报告（本地工具）
report = assistant.generate_learning_report("report.json")
```

---

## 🔍 调试和监控

### 查看 MCP 状态

```python
# 获取所有 MCP 连接状态
status = assistant.get_mcp_status()
print(status)
```

### 断开连接

```python
# 断开特定服务器
assistant.disconnect_mcp_server("filesystem")

# 断开所有连接
assistant.disconnect_mcp_server()
```

---

## 📦 依赖安装

```bash
# 安装 MCP 核心包
pip install "mcp[cli]" fastmcp python-dotenv

# 安装可选的 MCP 服务（需要 Node.js）
npm install -g @modelcontextprotocol/server-filesystem
npm install -g @modelcontextprotocol/server-git
```

---

## 🎯 实际测试

运行演示脚本：

```bash
# 运行 MCP 集成演示
python demo_mcp_integration.py

# 运行 MCP Client 演示
python mcp_client.py
```

---

## 💡 最佳实践

1. **安全性**: MCP Client 只连接可信的服务器
2. **错误处理**: 始终检查工具调用的返回结果
3. **资源管理**: 及时断开不需要的 MCP 连接
4. **日志记录**: 使用 NoteTool 记录重要的 MCP 操作
5. **性能优化**: 合理缓存 MCP 工具的调用结果

---

## 🚀 未来扩展

- 连接更多专业 MCP 服务（数据库、API、云服务等）
- 实现自定义 MCP 工具
- 支持 MCP SSE 和 Streamable HTTP 传输
- 添加 MCP 工具调用缓存
- 实现 MCP 工具组合编排

---

## 📞 获取帮助

- MCP 官方文档：https://modelcontextprotocol.io
- FastMCP 文档：https://github.com/modelcontextprotocol/python-sdk
- 项目 Issues: 提出问题和功能请求

---

**🎉 享受强大的 MCP 集成功能！**
