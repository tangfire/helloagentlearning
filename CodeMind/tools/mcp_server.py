"""
CodeMind MCP Server - 代码库智能维护助手 MCP 服务

提供 MCP（Model Context Protocol）服务器功能，向外部 AI 助手（如 Claude）暴露：
1. 代码库探索工具
2. 文档问答工具
3. 任务管理工具
4. 上下文管理工具
"""

from fastmcp import FastMCP
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# 导入 CodeMind 核心组件
from codemind_assistant import CodeMindAssistant
from note_tool import NoteTool
from terminal_tool import TerminalTool
from context_builder import ContextBuilder


# 创建 MCP 服务器实例
mcp = FastMCP(
    name="CodeMind Assistant",
    instructions="""
    CodeMind Assistant - 代码库智能维护助手
    
    这是一个专业的代码库维护工具，能够：
    - 探索和理解 Python 代码库结构
    - 基于文档和代码进行智能问答
    - 记录和管理技术债务、重构任务
    - 维护跨会话的上下文连贯性
    
    使用场景：
    1. 代码库理解与探索
    2. 技术债务识别与管理
    3. 长期重构任务追踪
    4. 智能文档问答
    """
)


# 全局助手实例（延迟初始化）
_assistant: Optional[CodeMindAssistant] = None


def get_assistant() -> CodeMindAssistant:
    """获取或创建 CodeMind 助手实例"""
    global _assistant
    if _assistant is None:
        project_path = os.getenv("CODEMIND_PROJECT_PATH", Path.cwd())
        notes_storage = os.getenv("CODEMIND_NOTES_STORAGE")
        
        _assistant = CodeMindAssistant(
            user_id=os.getenv("CODEMIND_USER_ID", "mcp_user"),
            project_path=str(project_path),
            notes_storage=notes_storage
        )
    
    return _assistant


# ==================== MCP Tools ====================

@mcp.tool()
def explore_codebase(command: str = "dir") -> Dict[str, Any]:
    """
    探索代码库结构
    
    Args:
        command: 要执行的命令（支持 dir, find, tree 等）
        
    Returns:
        命令执行结果
        
    示例:
        - "dir" - 列出当前目录
        - "dir /s" - 递归列出所有文件
        - "find . -name '*.py'" - 查找所有 Python 文件
    """
    assistant = get_assistant()
    result = assistant.explore_codebase(command, save_to_notes=False)
    
    return {
        "success": result["success"],
        "output": result.get("stdout", "") or result.get("stderr", ""),
        "command": command
    }


@mcp.tool()
def analyze_file(file_path: str) -> Dict[str, Any]:
    """
    分析文件结构和内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件分析结果，包括统计信息、内容预览等
    """
    assistant = get_assistant()
    result = assistant.analyze_file(file_path)
    
    return {
        "file_name": result.get("filename", ""),
        "stats": result.get("stats", {}),
        "preview": result.get("content_preview", "")[:500],  # 限制预览长度
        "structure": result.get("structure", {})
    }


@mcp.tool()
def search_in_codebase(pattern: str, file_pattern: str = "*.py") -> Dict[str, Any]:
    """
    在代码库中搜索模式
    
    Args:
        pattern: 搜索模式（正则表达式）
        file_pattern: 文件匹配模式（如 *.py, *.txt）
        
    Returns:
        搜索结果
    """
    assistant = get_assistant()
    result = assistant.search_in_codebase(pattern, file_pattern)
    
    return {
        "pattern": pattern,
        "file_pattern": file_pattern,
        "matches": result.get("matches", []),
        "count": len(result.get("matches", []))
    }


@mcp.tool()
def ask_question(question: str, use_mqe: bool = True, use_hyde: bool = True) -> Dict[str, Any]:
    """
    基于文档和代码的智能问答
    
    Args:
        question: 问题内容
        use_mqe: 是否使用多查询扩展（默认 True）
        use_hyde: 是否使用假设文档嵌入（默认 True）
        
    Returns:
        答案和相关信息
    """
    assistant = get_assistant()
    result = assistant.ask(question, use_mqe=use_mqe, use_hyde=use_hyde)
    
    return {
        "question": question,
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "confidence": result.get("confidence", 0.0)
    }


@mcp.tool()
def create_task(title: str, description: str = "", priority: str = "medium", 
                tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    创建任务或记录问题
    
    Args:
        title: 任务标题
        description: 任务描述
        priority: 优先级（low, medium, high, critical）
        tags: 标签列表
        
    Returns:
        创建的任务 ID 和信息
    """
    assistant = get_assistant()
    
    if tags is None:
        tags = ["mcp"]
    elif "mcp" not in tags:
        tags.append("mcp")
    
    task_id = assistant.create_task(
        title=title,
        description=description,
        priority=priority,
        tags=tags
    )
    
    return {
        "task_id": task_id,
        "title": title,
        "status": "created"
    }


@mcp.tool()
def list_tasks(status: str = "open", limit: int = 20) -> List[Dict[str, Any]]:
    """
    列出任务/笔记
    
    Args:
        status: 任务状态（open, in_progress, resolved, closed）
        limit: 返回数量限制
        
    Returns:
        任务列表
    """
    assistant = get_assistant()
    summary = assistant.get_task_summary()
    
    # 获取指定状态的笔记
    notes = assistant.note_tool.search_notes(status=status)
    
    return [
        {
            "id": note.id,
            "title": note.title,
            "type": note.note_type,
            "priority": note.priority,
            "status": note.status,
            "tags": note.tags,
            "created_at": note.created_at
        }
        for note in notes[:limit]
    ]


@mcp.tool()
def update_task_status(task_id: str, status: str, content: str = "") -> Dict[str, Any]:
    """
    更新任务状态或内容
    
    Args:
        task_id: 任务 ID
        status: 新状态
        content: 更新内容（可选）
        
    Returns:
        更新结果
    """
    assistant = get_assistant()
    
    success = assistant.note_tool.update_note(
        note_id=task_id,
        status=status,
        content=content if content else None
    )
    
    return {
        "task_id": task_id,
        "success": success,
        "new_status": status
    }


@mcp.tool()
def load_document(file_path: str) -> Dict[str, Any]:
    """
    加载文档到知识库
    
    Args:
        file_path: 文件路径（PDF, TXT, MD 等）
        
    Returns:
        加载结果
    """
    assistant = get_assistant()
    success = assistant.load_document(file_path)
    
    return {
        "file_path": file_path,
        "success": success,
        "message": "文档加载成功" if success else "文档加载失败"
    }


@mcp.tool()
def get_context(query: str) -> str:
    """
    获取与查询相关的历史上下文
    
    Args:
        query: 查询关键词
        
    Returns:
        格式化的上下文字符串
    """
    assistant = get_assistant()
    context = assistant.context_builder.build_context(query)
    
    return context if context else "未找到相关上下文"


@mcp.tool()
def get_project_stats() -> Dict[str, Any]:
    """
    获取项目统计信息
    
    Returns:
        包含各种统计数据的字典
    """
    assistant = get_assistant()
    stats = assistant.get_stats()
    
    return {
        "session_info": {
            "user_id": stats.get("user_id", "unknown"),
            "session_duration": str(stats.get("session_duration", "")),
            "documents_loaded": stats.get("documents_loaded", 0),
            "questions_answered": stats.get("questions_asked", 0)
        },
        "tools_usage": {
            "commands_executed": stats.get("tools_usage", {}).get("commands_executed", 0),
            "notes_created": stats.get("tools_usage", {}).get("notes_created", 0),
            "context_entries": stats.get("tools_usage", {}).get("context_entries", 0)
        },
        "performance": {
            "avg_context_quality": stats.get("context_engineering", {}).get("avg_context_quality", 0.0),
            "compressions_performed": stats.get("context_engineering", {}).get("compressions_performed", 0)
        }
    }


# ==================== MCP Resources ====================

@mcp.resource("codemind://tasks/{task_id}")
def get_task_resource(task_id: str) -> str:
    """
    获取特定任务的详细信息
    
    Args:
        task_id: 任务 ID
        
    Returns:
        任务详情字符串
    """
    assistant = get_assistant()
    
    # 搜索特定任务
    notes = assistant.note_tool.search_notes()
    for note in notes:
        if note.id == task_id:
            return f"""
任务详情：
- ID: {note.id}
- 标题：{note.title}
- 类型：{note.note_type}
- 优先级：{note.priority}
- 状态：{note.status}
- 标签：{', '.join(note.tags)}
- 创建时间：{note.created_at}
- 更新时间：{note.updated_at}

内容：
{note.content}
"""
    
    return "任务不存在"


@mcp.resource("codemind://files/{filepath:path}")
def get_file_resource(filepath: str) -> str:
    """
    获取文件内容
    
    Args:
        filepath: 文件路径
        
    Returns:
        文件内容
    """
    assistant = get_assistant()
    result = assistant.analyze_file(filepath)
    
    if "error" in result:
        return f"错误：{result['error']}"
    
    return f"""
文件：{result.get('filename', '')}
大小：{result.get('stats', {}).get('size', 'N/A')} 字节
行数：{result.get('stats', {}).get('lines', 'N/A')}

内容预览：
{result.get('preview', '')}
"""


# ==================== MCP Prompts ====================

@mcp.prompt()
def code_review_prompt(file_path: str) -> str:
    """
    代码审查提示词模板
    
    Args:
        file_path: 要审查的文件路径
        
    Returns:
        格式化的提示词
    """
    return f"""
请对以下文件进行代码审查：{file_path}

审查要点：
1. 代码质量和可读性
2. 潜在的错误和边界情况
3. 性能优化建议
4. 最佳实践遵循情况
5. 测试覆盖建议

请使用 analyze_file 工具获取文件内容，然后提供详细的审查意见。
"""


@mcp.prompt()
def refactoring_plan_prompt(issue_description: str) -> str:
    """
    重构计划提示词模板
    
    Args:
        issue_description: 问题描述
        
    Returns:
        格式化的提示词
    """
    return f"""
针对以下技术问题，请制定详细的重构计划：

{issue_description}

重构计划应包含：
1. 问题分析和影响范围
2. 重构目标和预期效果
3. 具体实施步骤
4. 风险评估和缓解措施
5. 测试策略

请使用 create_task 工具创建相关任务，并记录关键决策。
"""


# ==================== 启动函数 ====================

def run_server():
    """运行 MCP 服务器"""
    print("🚀 启动 CodeMind MCP Server...")
    print(f"   工作目录：{Path.cwd()}")
    print(f"   服务器名称：CodeMind Assistant")
    print(f"   可用工具：10 个")
    print(f"   可用资源：2 个")
    print(f"   可用提示词：2 个")
    print("\n💡 使用方式:")
    print("   1. Claude Desktop: 配置 MCP server 连接")
    print("   2. CLI: mcp dev mcp_server.py")
    print("   3. HTTP: mcp serve mcp_server.py --transport http\n")
    
    mcp.run()


if __name__ == "__main__":
    run_server()
