"""
CodeMind Assistant 快速演示脚本

展示 CodeMind 的核心功能：
1. 文档加载和问答
2. 代码库探索
3. 任务管理
4. 上下文工程
"""

import os
from pathlib import Path
from codemind_assistant import CodeMindAssistant


def demo_codemind():
    """CodeMind 功能演示"""
    
    print("=" * 80)
    print("🚀 CodeMind Assistant - 快速演示")
    print("=" * 80)
    
    # 创建助手实例
    assistant = CodeMindAssistant(
        user_id="demo_user",
        project_path=str(Path.cwd())
    )
    
    # ========== 场景 1: 加载文档并问答 ==========
    print("\n" + "=" * 80)
    print("📄 场景 1: 文档加载和智能问答")
    print("=" * 80)
    
    pdf_path = "Happy-LLM-0727.pdf"
    if not os.path.exists(pdf_path):
        pdf_path = "01_hello_agent/Happy-LLM-0727.pdf"
    
    if os.path.exists(pdf_path):
        print(f"\n加载文档：{pdf_path}")
        assistant.load_document(pdf_path)
        
        # 测试问答
        question = "什么是注意力机制？"
        print(f"\n提问：{question}")
        
        result = assistant.ask(question, use_mqe=True, use_hyde=True)
        
        print(f"\n回答：{result['answer'][:300]}...")
        print(f"检索方法：{result['retrieval_method']}")
        print(f"来源数量：{result['num_sources']} 个文档片段")
    
    # ========== 场景 2: 代码库探索 ==========
    print("\n" + "=" * 80)
    print("💻 场景 2: 代码库探索")
    print("=" * 80)
    
    # 查看当前目录结构
    print("\n查看项目结构:")
    assistant.explore_codebase("ls -la")
    
    # 搜索 Python 文件
    print("\n查找所有 Python 文件:")
    assistant.explore_codebase("find . -name '*.py' -type f | head -10")
    
    # ========== 场景 3: 文件分析 ==========
    print("\n" + "=" * 80)
    print("🔍 场景 3: 文件分析")
    print("=" * 80)
    
    file_to_analyze = "codemind_assistant.py"
    print(f"\n分析文件：{file_to_analyze}")
    
    file_info = assistant.analyze_file(file_to_analyze)
    print(f"文件大小：{file_info['stats'].get('size_kb', 0)} KB")
    print(f"行数：{file_info['stats'].get('lines', -1)} 行")
    
    # ========== 场景 4: 代码搜索 ==========
    print("\n" + "=" * 80)
    print("🔎 场景 4: 代码搜索")
    print("=" * 80)
    
    search_pattern = "class.*Assistant"
    print(f"\n搜索模式：'{search_pattern}'")
    
    search_result = assistant.search_in_codebase(search_pattern, "*.py")
    print(f"搜索结果预览:\n{search_result[:500]}...")
    
    # ========== 场景 5: 任务管理 ==========
    print("\n" + "=" * 80)
    print("✅ 场景 5: 任务管理")
    print("=" * 80)
    
    # 创建任务
    task_id = assistant.create_task(
        title="优化代码结构",
        description="重构 codemind_assistant.py，提高代码质量",
        priority="high",
        tags=["refactor", "code_quality"],
        related_files=[file_to_analyze]
    )
    print(f"\n创建任务 ID: {task_id}")
    
    # 创建观察笔记
    observation_id = assistant.note_tool.create_note(
        title="代码库观察",
        content=f"项目包含多个 Python 文件，使用 LangChain 框架构建",
        note_type="observation",
        tags=["codebase", "structure"]
    ).id
    print(f"创建观察笔记 ID: {observation_id}")
    
    # 查看任务摘要
    task_summary = assistant.get_task_summary()
    print(f"\n任务摘要:")
    print(f"  - 总笔记数：{task_summary['total_notes']}")
    print(f"  - 待处理问题：{task_summary['open_issues']}")
    print(f"  - 进行中任务：{task_summary['pending_tasks']}")
    
    # ========== 场景 6: 上下文管理 ==========
    print("\n" + "=" * 80)
    print("🧠 场景 6: 上下文管理")
    print("=" * 80)
    
    # 设置优先话题
    assistant.context_builder.set_priority_topics(["code_quality", "refactor"])
    
    # 构建针对当前问题的上下文
    context = assistant.context_builder.build_context(
        current_query="如何优化代码结构？",
        include_types=["note", "task_update", "code_analysis"]
    )
    
    print(f"\n构建的上下文长度：{len(context)} 字符")
    print(f"上下文条目数：{len(assistant.context_builder.context_history)}")
    
    # 查看上下文摘要
    ctx_summary = assistant.context_builder.get_summary()
    print(f"上下文统计:")
    print(f"  - 总条目数：{ctx_summary['total_entries']}")
    print(f"  - 总长度：{ctx_summary['total_length']} 字符")
    
    # ========== 场景 7: 生成学习报告 ==========
    print("\n" + "=" * 80)
    print("📊 场景 7: 生成学习报告")
    print("=" * 80)
    
    report = assistant.generate_learning_report("demo_report.json")
    
    print(f"\n报告统计:")
    print(f"  - 加载文档：{report['rag_statistics']['documents_loaded']}")
    print(f"  - 回答问题：{report['rag_statistics']['questions_asked']}")
    print(f"  - 创建笔记：{report['notes']['total_notes']}")
    print(f"  - 执行命令：{report['terminal']['total_commands']}")
    print(f"  - 平均上下文质量：{report['rag_statistics']['avg_context_quality']:.2f}/1.00")
    
    # ========== 完整统计 ==========
    stats = assistant.get_stats()
    
    print("\n" + "=" * 80)
    print("📈 完整统计信息")
    print("=" * 80)
    
    print(f"\n会话时长：{stats['session_duration']}")
    print(f"总记忆数：{stats['total_memories']}")
    print(f"上下文工程质量:")
    print(f"  - 压缩执行次数：{stats['context_engineering']['compressions_performed']}")
    print(f"  - 平均上下文质量：{stats['context_engineering']['avg_context_quality']:.3f}")
    print(f"工具使用情况:")
    print(f"  - 执行命令数：{stats['tools_usage']['commands_executed']}")
    print(f"  - 创建笔记数：{stats['tools_usage']['notes_created']}")
    print(f"  - 上下文条目数：{stats['tools_usage']['context_entries']}")
    
    print("\n" + "=" * 80)
    print("✅ CodeMind 演示完成！")
    print("=" * 80)
    
    return assistant


if __name__ == "__main__":
    demo_codemind()
