"""
修复 Milvus 集合 - 删除旧集合并重建
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.milvus_client import get_milvus_client

def fix_milvus_collection():
    """删除旧集合并重建"""
    print("=" * 80)
    print("🔧 修复 Milvus 集合")
    print("=" * 80)
    
    milvus = get_milvus_client()
    
    # 1. 删除旧集合
    print("\n1️⃣ 删除旧集合...")
    try:
        milvus.drop_collection()
        print("✅ 旧集合已删除")
    except Exception as e:
        print(f"ℹ️ 集合不存在或已删除：{e}")
    
    # 2. 重新初始化（会自动创建新集合和索引）
    print("\n2️⃣ 重新创建集合和索引...")
    try:
        # 强制重新初始化
        milvus._init_collection()
        print("✅ 集合和索引已重建")
    except Exception as e:
        print(f"❌ 重建失败：{e}")
        return
    
    # 3. 验证
    print("\n3️⃣ 验证集合状态...")
    try:
        stats = milvus.get_collection_stats()
        print(f"✅ 集合统计：{stats}")
    except Exception as e:
        print(f"❌ 验证失败：{e}")
    
    print("\n" + "=" * 80)
    print("✅ Milvus 修复完成！")
    print("=" * 80)

if __name__ == "__main__":
    fix_milvus_collection()
