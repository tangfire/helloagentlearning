"""
CodeMind Assistant MCP 集成演示

展示如何使用 MCP 功能：
1. 作为 MCP Server 对外提供服务
2. 作为 MCP Client 连接外部服务
"""

import asyncio
from pathlib import Path
from codemind_assistant import CodeMindAssistant


def demo_mcp_server_info():
    """演示 MCP Server 信息"""
    print("=" * 80)
    print("🚀 CodeMind MCP Server 信息")
    print("=" * 80)
    
    print("\n📋 MCP Server 功能:")
    print("  - 10 个可用工具:")
    print("    1. explore_codebase - 代码库探索")
    print("    2. analyze_file - 文件分析")
    print("    3. search_in_codebase - 代码搜索")
    print("    4. ask_question - 智能问答")
    print("    5. create_task - 创建任务")
    print("    6. list_tasks - 列出任务")
    print("    7. update_task_status - 更新任务")
    print("    8. load_document - 加载文档")
    print("    9. get_context - 获取上下文")
    print("    10. get_project_stats - 项目统计")
    
    print("\n  - 2 个资源:")
    print("    1. codemind://tasks/{task_id} - 任务详情")
    print("    2. codemind://files/{filepath} - 文件内容")
    
    print("\n  - 2 个提示词模板:")
    print("    1. code_review_prompt - 代码审查")
    print("    2. refactoring_plan_prompt - 重构计划")
    
    print("\n💡 启动方式:")
    print("  方法 1: python mcp_server.py")
    print("  方法 2: mcp dev mcp_server.py")
    print("  方法 3: mcp serve mcp_server.py --transport http")
    
    print("\n" + "=" * 80)


async def demo_mcp_client(assistant: CodeMindAssistant):
    """演示 MCP Client 功能"""
    print("\n" + "=" * 80)
    print("🔌 MCP Client 连接演示")
    print("=" * 80)
    
    # 注意：实际使用需要安装对应的 MCP 服务器
    # 这里仅做演示，不实际连接
    
    print("\n[步骤 1] 查看 MCP 状态...")
    status = assistant.get_mcp_status()
    print(f"MCP 可用性：{status.get('available', False)}")
    
    if status.get('available'):
        print(f"已连接服务器数：{status.get('connected_servers', 0)}")
        
        # 演示连接（注释掉，实际需要对应环境）
        print("\n[步骤 2] 可连接的 MCP 服务:")
        print("  - filesystem: npx -y @modelcontextprotocol/server-filesystem")
        print("  - git: npx -y @modelcontextprotocol/server-git")
        print("  - database: python -m mcp_server_database")
        
        # 示例：连接文件系统（需要 Node.js 和 npx）
        # print("\n[步骤 3] 尝试连接文件系统 MCP 服务...")
        # success = assistant.connect_to_mcp_server(
        #     "filesystem",
        #     command="npx",
        #     args=["-y", "@modelcontextprotocol/server-filesystem", str(Path.cwd())]
        # )
        
        # if success:
        #     # 调用文件系统工具
        #     result = await assistant.call_mcp_tool(
        #         "filesystem",
        #         "read_directory",
        #         {"path": str(Path.cwd())}
        #     )
        #     print(f"目录列表：{result}")
        
        # 示例：连接 Git MCP 服务
        # print("\n[步骤 4] 尝试连接 Git MCP 服务...")
        # success = assistant.connect_to_mcp_server(
        #     "git",
        #     command="npx",
        #     args=["-y", "@modelcontextprotocol/server-git"]
        # )
        
        # if success:
        #     # 调用 Git 工具
        #     result = await assistant.call_mcp_tool(
        #         "git",
        #         "git_status",
        #         {"repository": str(Path.cwd())}
        #     )
        #     print(f"Git 状态：{result}")
    
    print("\n✅ MCP Client 演示完成")


def demo_mcp_integration():
    """演示完整的 MCP 集成"""
    print("\n" + "=" * 80)
    print("🔗 CodeMind MCP 集成完整演示")
    print("=" * 80)
    
    # 创建助手实例
    assistant = CodeMindAssistant(
        user_id="mcp_demo_user",
        project_path=str(Path.cwd())
    )
    
    # 演示 1: MCP Server 信息
    demo_mcp_server_info()
    
    # 演示 2: MCP Client 功能
    asyncio.run(demo_mcp_client(assistant))
    
    # 演示 3: 结合本地工具和 MCP 工具
    print("\n" + "=" * 80)
    print("🛠️ 混合工具使用演示")
    print("=" * 80)
    
    print("\n[场景] 代码库维护工作流:")
    print("  1. 使用本地 TerminalTool 探索代码库")
    print("  2. 使用 MCP FileSystem 工具读取特定文件")
    print("  3. 使用本地 NoteTool 记录发现的问题")
    print("  4. 使用 MCP Git 工具提交更改")
    print("  5. 使用本地 TaskManager 追踪长期任务")
    
    print("\n实际执行（本地工具）:")
    # 使用本地工具
    result = assistant.explore_codebase("dir", save_to_notes=False)
    if result["success"]:
        output = result.get("stdout", "") or result.get("stderr", "")
        lines = output.split('\n')
        print(f"  ✓ 代码库探索成功，共 {len(lines)} 行输出")
    
    # 创建任务记录
    task_id = assistant.create_task(
        title="MCP 集成测试",
        description="验证 MCP Server 和 Client 功能",
        priority="medium",
        tags=["mcp", "testing"]
    )
    print(f"  ✓ 创建任务：{task_id}")
    
    # 查看 MCP 状态
    mcp_status = assistant.get_mcp_status()
    print(f"  ✓ MCP 状态：{'可用' if mcp_status.get('available') else '不可用'}")
    
    print("\n" + "=" * 80)
    print("✅ CodeMind MCP 集成演示完成！")
    print("=" * 80)
    
    print("\n📝 总结:")
    print("  - MCP Server: 提供 10 个工具、2 个资源、2 个提示词")
    print("  - MCP Client: 可连接外部 MCP 服务扩展能力")
    print("  - 本地工具：TerminalTool, NoteTool, ContextBuilder")
    print("  - 混合使用：本地工具 + MCP 工具协同工作")
    
    print("\n🚀 下一步:")
    print("  1. 运行 'python mcp_server.py' 启动 MCP 服务")
    print("  2. 在 Claude Desktop 中配置 MCP server 连接")
    print("  3. 使用 MCP Client 连接更多外部服务")
    print("  4. 享受强大的代码库维护能力！")


if __name__ == "__main__":
    demo_mcp_integration()
