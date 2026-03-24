"""
PDFLearningAssistant 简单测试脚本
"""

from pdf_assistant import PDFLearningAssistant
import os

def test_basic_functionality():
    """测试基本功能"""
    print("=" * 60)
    print("测试 1: 创建助手实例")
    print("=" * 60)
    
    assistant = PDFLearningAssistant(user_id="test_user")
    print(f"✓ 助手创建成功，用户 ID: {assistant.user_id}")
    print(f"✓ 会话 ID: {assistant.session_id}")
    
    print("\n" + "=" * 60)
    print("测试 2: 查看初始状态")
    print("=" * 60)
    
    stats = assistant.get_stats()
    print(f"初始统计信息:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")
    
    print("\n" + "=" * 60)
    print("测试 3: 尝试提问（未加载文档）")
    print("=" * 60)
    
    result = assistant.ask("你好，请问 LangChain 是什么？")
    print(f"问题：{result.get('question', 'N/A')}")
    print(f"回答：{result.get('answer', 'No answer')}")
    
    print("\n" + "=" * 60)
    print("测试 4: 检查环境变量")
    print("=" * 60)
    
    env_vars = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "未设置"),
        "MODEL": os.getenv("MODEL", "未设置"),
        "BASE_URL": os.getenv("BASE_URL", "未设置")
    }
    
    for key, value in env_vars.items():
        status = "✓ 已配置" if value != "未设置" else "✗ 未配置"
        print(f"{key}: {status}")
    
    print("\n" + "=" * 60)
    print("所有基础测试完成！")
    print("=" * 60)
    print("\n提示：要测试完整的问答功能，请:")
    print("1. 确保 .env 文件中配置了 OPENAI_API_KEY 等环境变量")
    print("2. 准备一个 PDF 文件")
    print("3. 调用 assistant.load_document('your_file.pdf')")
    print("4. 调用 assistant.ask('你的问题')")


if __name__ == "__main__":
    test_basic_functionality()
