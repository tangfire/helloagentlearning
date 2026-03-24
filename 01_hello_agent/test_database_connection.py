"""
测试数据库连接 - 验证 PostgreSQL 和 Milvus 是否正常连接
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.db_connection import check_connection, get_db_context
from database.milvus_client import get_milvus_client
from sqlalchemy import text

def test_postgresql():
    """测试 PostgreSQL 连接"""
    print("=" * 80)
    print("🐘 测试 PostgreSQL 连接")
    print("=" * 80)
    
    if not check_connection():
        print("❌ PostgreSQL 连接失败！")
        print("\n请检查：")
        print("1. WSL2 中的 Docker 是否运行")
        print("2. PostgreSQL 容器是否启动：docker ps")
        print("3. .env 文件中的配置是否正确")
        return False
    
    # 测试查询
    try:
        with get_db_context() as db:
            result = db.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ PostgreSQL 版本：{version[:50]}...")
            
            # 检查表是否存在
            result = db.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                print(f"✅ 数据库表已创建：{len(tables)} 个表")
                for table in tables[:5]:  # 只显示前 5 个
                    print(f"   - {table}")
                if len(tables) > 5:
                    print(f"   ... 还有 {len(tables) - 5} 个表")
            else:
                print("⚠️  数据库中没有表，需要运行 init_database.py 初始化")
            
            return True
            
    except Exception as e:
        print(f"❌ 数据库查询失败：{e}")
        return False

def test_milvus():
    """测试 Milvus 连接"""
    print("\n" + "=" * 80)
    print("🔷 测试 Milvus 向量数据库连接")
    print("=" * 80)
    
    try:
        client = get_milvus_client()
        stats = client.get_collection_stats()
        
        print(f"✅ Milvus 集合统计：")
        print(f"   - 集合名称：{stats.get('name', 'N/A')}")
        print(f"   - 向量数量：{stats.get('count', 0)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Milvus 连接失败：{e}")
        print("\n请检查：")
        print("1. WSL2 中的 Docker 是否运行")
        print("2. Milvus 容器是否启动：docker ps")
        print("3. .env 文件中的 MILVUS_HOST 和 MILVUS_PORT 配置")
        return False

def test_redis():
    """测试 Redis 连接"""
    print("\n" + "=" * 80)
    print("🔴 测试 Redis 缓存连接")
    print("=" * 80)
    
    try:
        import redis
        from pathlib import Path as PathLib
        import os
        
        # 从 .env 文件读取配置
        env_path = project_root / ".env"
        if env_path.exists():
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('REDIS_HOST='):
                        redis_host = line.split('=')[1].strip()
                    elif line.startswith('REDIS_PORT='):
                        redis_port = int(line.split('=')[1].strip())
        else:
            redis_host = 'localhost'
            redis_port = 6379
        
        r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
        r.ping()
        
        print(f"✅ Redis 连接成功：{redis_host}:{redis_port}")
        
        # 测试读写
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        print(f"✅ Redis 读写测试：{value}")
        
        return True
        
    except ImportError:
        print("⚠️  redis 未安装，跳过测试")
        return True
    except Exception as e:
        print(f"❌ Redis 连接失败：{e}")
        print("\n请检查：")
        print("1. WSL2 中的 Docker 是否运行")
        print("2. Redis 容器是否启动：docker ps")
        print("3. .env 文件中的 REDIS_HOST 和 REDIS_PORT 配置")
        return False

def main():
    """主函数"""
    print("\n🚀 开始测试数据库连接...\n")
    
    postgres_ok = test_postgresql()
    milvus_ok = test_milvus()
    redis_ok = test_redis()
    
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)
    print(f"PostgreSQL: {'✅ 正常' if postgres_ok else '❌ 失败'}")
    print(f"Milvus:     {'✅ 正常' if milvus_ok else '❌ 失败'}")
    print(f"Redis:      {'✅ 正常' if redis_ok else '❌ 失败'}")
    
    if postgres_ok and milvus_ok and redis_ok:
        print("\n🎉 所有数据库连接正常！可以开始使用持久化存储了。")
        print("\n💡 下一步：")
        print("1. 启动 Web 应用：python start_web_app.py")
        print("2. 访问前端：http://localhost:8000")
        print("3. 创建工作空间并上传文档")
        return True
    else:
        print("\n❌ 部分数据库连接失败，请先解决连接问题。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
