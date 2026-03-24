"""
测试上下文工程功能

演示先进的上下文工程技术：
1. 上下文压缩 - 提取最相关信息
2. 上下文排序 - 按相关性排序
3. 动态窗口调整 - 自适应上下文长度
4. 上下文质量评估 - 量化上下文质量
5. 多源上下文融合 - 整合 MQE 和 HyDE 结果
"""

import os
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from advanced_pdf_assistant import AdvancedPDFLearningAssistant


def test_context_engineering():
    """测试上下文工程的完整流程"""
    
    print("=" * 80)
    print("🚀 上下文工程功能演示")
    print("=" * 80)
    
    # 创建助手实例
    assistant = AdvancedPDFLearningAssistant(user_id="test_user")
    
    # 加载文档
    pdf_path = "Happy-LLM-0727.pdf"
    if not os.path.exists(pdf_path):
        pdf_path = "CodeMind/Happy-LLM-0727.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"\n❌ 未找到 PDF 文件：{pdf_path}")
        return
    
    print(f"\n📄 加载文档：{pdf_path}")
    assistant.load_document(pdf_path)
    
    # 测试问题
    test_questions = [
        {
            "question": "什么是 RAG（检索增强生成）？",
            "description": "基础概念题 - 测试上下文质量评估"
        },
        {
            "question": "如何优化向量检索的性能和准确性？",
            "description": "技术实现题 - 测试上下文压缩和排序"
        },
        {
            "question": "比较 MQE 和 HyDE 两种检索策略的优缺点",
            "description": "综合分析题 - 测试多源上下文融合"
        }
    ]
    
    print("\n" + "=" * 80)
    print("📝 开始测试上下文工程")
    print("=" * 80)
    
    results = []
    
    for i, test_case in enumerate(test_questions, 1):
        print(f"\n\n{'='*80}")
        print(f"【测试 {i}】{test_case['description']}")
        print(f"问题：{test_case['question']}")
        print('='*80)
        
        # 提问
        result = assistant.ask(
            test_case['question'],
            use_mqe=True,
            use_hyde=True
        )
        
        # 显示结果
        print(f"\n【回答摘要】")
        print(result['answer'][:500] + "...")
        
        print(f"\n【检索方法】{result['retrieval_method']}")
        print(f"【来源数量】{result['num_sources']} 个文档片段")
        
        results.append(result)
    
    # 获取统计信息
    print("\n" + "=" * 80)
    print("📊 上下文工程统计")
    print("=" * 80)
    
    stats = assistant.get_stats()
    
    print(f"\n基础统计:")
    print(f"  - 加载文档数：{stats['documents_loaded']}")
    print(f"  - 创建文本块：{stats['chunks_created']}")
    print(f"  - 回答问题数：{stats['questions_asked']}")
    print(f"  - MQE 查询生成：{stats['mqe_queries_generated']}")
    print(f"  - HyDE 假设生成：{stats['hyde_hypotheses_generated']}")
    
    print(f"\n上下文工程统计:")
    context_stats = stats['context_engineering']
    print(f"  - 压缩执行次数：{context_stats['compressions_performed']}")
    print(f"  - 平均上下文质量：{context_stats['avg_context_quality']:.3f}/1.000")
    print(f"  - 质量阈值：{context_stats['quality_threshold']}")
    print(f"  - 最大上下文长度：{context_stats['max_context_length']}")
    
    # 显示记忆统计
    print(f"\n记忆系统统计:")
    print(f"  - 总记忆数：{stats['total_memories']}")
    
    # 生成学习报告
    print("\n" + "=" * 80)
    print("📋 生成完整学习报告")
    print("=" * 80)
    
    report = assistant.generate_learning_report("context_engineering_report.json")
    
    print(f"\n报告已导出到：context_engineering_report.json")
    print(f"\n关键指标:")
    print(f"  - 情景记忆：{report['statistics']['total_episodic_memories']} 条")
    print(f"  - 语义记忆：{report['statistics']['total_semantic_memories']} 条")
    print(f"  - 感知记忆：{report['statistics']['total_perceptual_memories']} 条")
    print(f"  - RAG 统计：{report['rag_statistics']}")
    
    print("\n" + "=" * 80)
    print("✅ 上下文工程功能测试完成！")
    print("=" * 80)
    
    # 展示核心功能总结
    print("\n🎯 核心上下文工程功能总结:")
    print("""
    1. ✅ 上下文压缩 (Context Compression)
       - 使用 LLMChainExtractor 提取最相关信息
       - 减少 Token 消耗，提高响应速度
       - 保持答案质量和准确性
    
    2. ✅ 上下文排序 (Context Ranking)
       - 基于向量相似度计算相关性
       - 优先保留高质量文档片段
       - 支持质量阈值过滤
    
    3. ✅ 动态窗口调整 (Adaptive Context Window)
       - 根据输入长度自动调整上下文大小
       - 智能截断，保留最关键信息
       - 避免超出 LLM 上下文限制
    
    4. ✅ 上下文质量评估 (Quality Evaluation)
       - 多维度质量指标（相似度、多样性）
       - 实时反馈上下文质量
       - 支持决策优化
    
    5. ✅ 多源上下文融合 (Multi-source Fusion)
       - 整合 MQE 和 HyDE 多种检索结果
       - 智能去重和优先级排序
       - 提高信息覆盖度
    """)


if __name__ == "__main__":
    test_context_engineering()
