"""
CodeMind Assistant 快速测试 - 验证核心功能
"""

import os
from pathlib import Path
from codemind_assistant import CodeMindAssistant


def quick_test():
    """快速验证核心功能"""
    
    print("=" * 80)
    print("🚀 CodeMind Assistant - 快速功能验证")
    print("=" * 80)
    
    # 创建助手实例
    assistant = CodeMindAssistant(
        user_id="test_user",
        project_path=str(Path.cwd())
    )
    
    # ========== 测试 1: 代码库探索 ==========
    print("\n[测试 1] 代码库探索")
    print("-" * 80)
    
    # 使用 Windows 兼容的命令
    result = assistant.explore_codebase("dir", save_to_notes=False)
    print(f"命令执行结果：{result}")  # 调试信息
    if not result["success"]:
        print(f"错误输出：{result.get('stderr', 'N/A')}")
    assert result["success"], f"❌ 命令执行失败：{result.get('stderr', 'Unknown error')}"
    print("✅ TerminalTool 工作正常")
    
    # ========== 测试 2: 文件分析 ==========
    print("\n[测试 2] 文件分析")
    print("-" * 80)
    
    file_info = assistant.analyze_file("codemind_assistant.py")
    assert "stats" in file_info, "❌ 文件分析失败"
    print(f"✅ 文件分析成功：{file_info['stats'].get('lines', -1)} 行")
    
    # ========== 测试 3: 任务管理 ==========
    print("\n[测试 3] 任务管理")
    print("-" * 80)
    
    task_id = assistant.create_task(
        title="测试任务",
        description="验证 NoteTool 功能",
        priority="medium",
        tags=["test"]
    )
    assert task_id is not None, "❌ 任务创建失败"
    print(f"✅ 任务创建成功：{task_id}")
    
    # 查看摘要
    summary = assistant.get_task_summary()
    assert summary["total_notes"] > 0, "❌ 笔记统计异常"
    print(f"✅ 任务摘要正常：共 {summary['total_notes']} 条笔记")
    
    # ========== 测试 4: 上下文管理 ==========
    print("\n[测试 4] 上下文管理")
    print("-" * 80)
    
    assistant.context_builder.set_priority_topics(["test"])
    context = assistant.context_builder.build_context("测试查询")
    ctx_summary = assistant.context_builder.get_summary()
    print(f"✅ 上下文管理正常：{ctx_summary['total_entries']} 条记录")
    
    # ========== 测试 5: 统计信息 ==========
    print("\n[测试 5] 统计信息")
    print("-" * 80)
    
    stats = assistant.get_stats()
    print(f"✅ 统计信息完整:")
    print(f"   - 会话时长：{stats['session_duration']}")
    print(f"   - 执行命令数：{stats['tools_usage']['commands_executed']}")
    print(f"   - 创建笔记数：{stats['tools_usage']['notes_created']}")
    
    print("\n" + "=" * 80)
    print("✅ 所有核心功能验证通过！")
    print("=" * 80)
    
    return True


if __name__ == "__main__":
    try:
        quick_test()
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
