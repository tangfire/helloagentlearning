#!/usr/bin/env python3
"""
数据库连接测试脚本
测试 PostgreSQL 和 Milvus 的连接状态
"""

import sys

def test_postgresql():
    """测试 PostgreSQL 连接"""
    print("=" * 60)
    print("🧪 测试 PostgreSQL 连接...")
    print("=" * 60)
    
    try:
        from sqlalchemy import create_engine, text
        
        DATABASE_URL = "postgresql://codemind:codemind2024@localhost:5432/codemind"
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # 查询版本
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ PostgreSQL 连接成功！")
            print(f"   版本：{version[:50]}...")
            
            # 查询表数量
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            count = result.scalar()
            print(f"📊 数据表数量：{count}")
            
            # 查询所有表名
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            print(f"\n📋 数据表列表:")
            for table in tables:
                print(f"   - {table}")
            
            # 查询默认用户
            result = conn.execute(text("SELECT username, email, role FROM users"))
            users = result.fetchall()
            if users:
                print(f"\n👥 默认用户:")
                for user in users:
                    print(f"   - {user[0]} ({user[1]}) - 角色：{user[2]}")
            
            return True
            
    except ImportError as e:
        print(f"❌ 缺少依赖：{e}")
        print("   请运行：pip install psycopg2-binary sqlalchemy")
        return False
    except Exception as e:
        print(f"❌ PostgreSQL 连接失败：{e}")
        return False


def test_milvus():
    """测试 Milvus 连接"""
    print("\n" + "=" * 60)
    print("🧪 测试 Milvus 连接...")
    print("=" * 60)
    
    try:
        from pymilvus import connections, utility
        
        # 连接 Milvus
        connections.connect(host="localhost", port=19530)
        
        print(f"✅ Milvus 连接成功！")
        
        # 检查版本
        try:
            version = utility.get_server_version()
            print(f"   版本：{version}")
        except:
            print(f"   版本：无法获取")
        
        # 列出所有集合
        collections = utility.list_collections()
        print(f"\n📊 集合列表：{collections}")
        
        # 查看集合详情
        if collections:
            for collection_name in collections:
                try:
                    from pymilvus import Collection
                    collection = Collection(collection_name)
                    print(f"\n📋 集合 '{collection_name}' 详情:")
                    print(f"   - 描述：{collection.description}")
                    print(f"   - Schema 字段数：{len(collection.schema.fields)}")
                    print(f"   - 实体数量：{collection.num_entities}")
                    
                    # 显示字段信息
                    print(f"\n   字段列表:")
                    for field in collection.schema.fields:
                        print(f"     - {field.name} ({field.dtype.name})")
                        if field.is_primary:
                            print(f"       └─ 主键")
                        if field.auto_id:
                            print(f"       └─ 自增")
                            
                except Exception as e:
                    print(f"⚠️  无法获取集合详情：{e}")
        else:
            print("ℹ️  暂无集合（正常，首次启动）")
        
        return True
        
    except ImportError as e:
        print(f"❌ 缺少依赖：{e}")
        print("   请运行：pip install pymilvus")
        return False
    except Exception as e:
        print(f"❌ Milvus 连接失败：{e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🎯 CodeMind 数据库连接测试")
    print("=" * 60)
    
    postgres_success = test_postgresql()
    milvus_success = test_milvus()
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    print(f"PostgreSQL: {'✅ 成功' if postgres_success else '❌ 失败'}")
    print(f"Milvus:     {'✅ 成功' if milvus_success else '❌ 失败'}")
    
    if postgres_success and milvus_success:
        print("\n🎉 所有数据库连接正常！可以开始使用了！")
        return 0
    else:
        print("\n⚠️  部分数据库连接失败，请检查配置")
        return 1


if __name__ == "__main__":
    sys.exit(main())
