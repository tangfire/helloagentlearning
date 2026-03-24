"""
测试数据库增强版功能

验证 PostgreSQL + Milvus 双存储架构是否正常工作
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.codemind_assistant_db import CodeMindAssistantDB
from database.db_connection import get_db_context
from database.dao import UserDAO


def test_database_enhanced():
    """测试数据库增强版功能"""
    
    print("=" * 80)
    print("🧪 测试数据库增强版功能")
    print("=" * 80)
    
    # 1. 测试数据库连接
    print("\n1️⃣ 测试数据库连接...")
    try:
        with get_db_context() as db:
            user_dao = UserDAO(db)
            user = user_dao.get_default_user()
            if user:
                print(f"✅ PostgreSQL 连接成功，找到默认用户：{user.username}")
            else:
                print("⚠️  未找到默认用户")
    except Exception as e:
        print(f"❌ PostgreSQL 连接失败：{e}")
        return
    
    # 2. 测试 Milvus 连接
    print("\n2️⃣ 测试 Milvus 连接...")
    try:
        from database.milvus_client import get_milvus_client
        milvus = get_milvus_client()
        stats = milvus.get_collection_stats()
        print(f"✅ Milvus 连接成功，集合统计：{stats}")
    except Exception as e:
        print(f"❌ Milvus 连接失败：{e}")
        return
    
    # 3. 创建助手实例
    print("\n3️⃣ 创建数据库增强版助手...")
    try:
        assistant = CodeMindAssistantDB(
            workspace_id="00000000-0000-0000-0000-000000000001",
            user_id="00000000-0000-0000-0000-000000000001"
        )
        print(f"✅ 助手创建成功")
    except Exception as e:
        print(f"❌ 助手创建失败：{e}")
        return
    
    # 4. 获取统计信息
    print("\n4️⃣ 获取统计信息...")
    try:
        stats = assistant.get_stats()
        print(f"📊 当前统计：{stats}")
    except Exception as e:
        print(f"❌ 获取统计失败：{e}")
    
    # 5. 测试上传文档（如果存在测试文件）
    print("\n5️⃣ 测试文档上传...")
    test_file = project_root / "README.md"
    if test_file.exists():
        try:
            result = assistant.upload_document(str(test_file), filename="README.md")
            if result:
                print(f"✅ 文档上传成功")
                
                # 获取最新统计
                stats = assistant.get_stats()
                print(f"📊 上传后统计：{stats}")
            else:
                print(f"⚠️  文档上传返回 False")
        except Exception as e:
            print(f"❌ 文档上传失败：{e}")
    else:
        print(f"⚠️  未找到测试文件 README.md")
    
    # 6. 测试检索
    print("\n6️⃣ 测试智能问答...")
    try:
        response = assistant.ask("这个项目是做什么的？", use_context=True)
        print(f"💬 问题：这个项目是做什么的？")
        print(f"🤖 回答：{response.get('answer', 'No answer')[:200]}...")
        print(f"📚 使用上下文：{response.get('context_used', False)}")
        print(f"📎 来源数：{len(response.get('sources', []))}")
    except Exception as e:
        print(f"❌ 问答失败：{e}")
    
    print("\n" + "=" * 80)
    print("✅ 测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    test_database_enhanced()
