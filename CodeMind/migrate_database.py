"""
数据库迁移脚本执行器

用于执行 SQL 迁移文件，更新数据库结构
"""

import os
import sys
from pathlib import Path
from database.db_connection import get_db_context
from sqlalchemy import text

def run_migration(migration_file: str):
    """执行单个迁移文件"""
    
    # 获取当前脚本所在目录的父目录（CodeMind 目录）
    base_dir = Path(__file__).parent
    migration_path = base_dir / "database" / "init" / migration_file
    
    if not migration_path.exists():
        print(f"❌ 迁移文件不存在：{migration_file}")
        return False
    
    print(f"\n{'='*60}")
    print(f"📋 执行迁移：{migration_file}")
    print(f"{'='*60}")
    
    try:
        with open(migration_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        with get_db_context() as db:
            # 执行 SQL
            db.execute(text(sql_content))
            db.commit()
        
        print(f"✅ 迁移执行成功：{migration_file}")
        return True
        
    except Exception as e:
        print(f"❌ 迁移执行失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_migrations():
    """执行所有迁移"""
    
    # 获取当前脚本所在目录的父目录（CodeMind 目录）
    base_dir = Path(__file__).parent
    init_dir = base_dir / "database" / "init"
    
    if not init_dir.exists():
        print(f"❌ 迁移目录不存在：{init_dir}")
        return False
    
    # 获取所有 SQL 文件并按名称排序
    migration_files = sorted([f.name for f in init_dir.glob("*.sql")])
    
    if not migration_files:
        print("⚠️ 未找到迁移文件")
        return False
    
    print(f"\n📋 找到 {len(migration_files)} 个迁移文件:")
    for f in migration_files:
        print(f"   - {f}")
    
    success_count = 0
    for migration_file in migration_files:
        if run_migration(migration_file):
            success_count += 1
        else:
            print(f"\n⚠️ 迁移中断在：{migration_file}")
            break
    
    print(f"\n{'='*60}")
    print(f"✅ 完成：{success_count}/{len(migration_files)} 个迁移成功")
    print(f"{'='*60}\n")
    
    return success_count == len(migration_files)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔧 数据库迁移工具")
    print("="*60)
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        # 执行指定的迁移
        migration_file = sys.argv[1]
        success = run_migration(migration_file)
    else:
        # 执行所有迁移
        success = run_all_migrations()
    
    if success:
        print("🎉 数据库迁移完成！\n")
        sys.exit(0)
    else:
        print("⚠️  数据库迁移失败，请检查错误信息。\n")
        sys.exit(1)
