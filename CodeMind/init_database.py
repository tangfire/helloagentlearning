"""
数据库初始化脚本

用于启动 Docker 服务并初始化数据库
"""

import subprocess
import sys
import time
from pathlib import Path


def run_command(command, shell=True):
    """运行命令并输出结果"""
    print(f"🚀 执行命令：{command}")
    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 命令执行失败：{e}")
        print(e.stderr)
        return False


def start_docker_services():
    """启动 Docker Compose 服务"""
    print("=" * 80)
    print("🚀 启动 Docker Compose 服务...")
    print("=" * 80)
    
    # 切换到 docker-compose.yml 所在目录
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # 停止并清理现有容器
    run_command("docker-compose down")
    
    # 启动所有服务
    success = run_command("docker-compose up -d")
    
    if not success:
        print("❌ Docker 服务启动失败")
        return False
    
    print("✅ Docker 服务已启动")
    return True


def wait_for_services():
    """等待服务就绪"""
    print("\n⏳ 等待服务启动...")
    
    services = [
        ("PostgreSQL", 5432),
        ("Milvus", 19530),
        ("Redis", 6379),
    ]
    
    for service_name, port in services:
        print(f"\n🔍 检查 {service_name} (端口 {port})...")
        max_retries = 30
        retry_delay = 5
        
        for i in range(max_retries):
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    print(f"✅ {service_name} 已就绪")
                    break
                else:
                    if i < max_retries - 1:
                        print(f"  ⏳ 等待中... ({i+1}/{max_retries})")
                        time.sleep(retry_delay)
            except Exception as e:
                if i < max_retries - 1:
                    print(f"  ⏳ 等待中... ({i+1}/{max_retries})")
                    time.sleep(retry_delay)
        else:
            print(f"❌ {service_name} 启动超时")
            return False
    
    return True


def test_postgresql():
    """测试 PostgreSQL 连接"""
    print("\n" + "=" * 80)
    print("🧪 测试 PostgreSQL 连接...")
    print("=" * 80)
    
    try:
        from database.db_connection import check_connection
        if check_connection():
            print("✅ PostgreSQL 连接成功")
            return True
        else:
            print("❌ PostgreSQL 连接失败")
            return False
    except Exception as e:
        print(f"❌ PostgreSQL 测试失败：{e}")
        return False


def test_milvus():
    """测试 Milvus 连接"""
    print("\n" + "=" * 80)
    print("🧪 测试 Milvus 连接...")
    print("=" * 80)
    
    try:
        from database.milvus_client import get_milvus_client
        client = get_milvus_client()
        stats = client.get_collection_stats()
        print(f"✅ Milvus 连接成功")
        print(f"📊 集合统计：{stats}")
        return True
    except Exception as e:
        print(f"❌ Milvus 测试失败：{e}")
        return False


def main():
    """主函数"""
    import os
    global os  # 在函数内部导入以避免循环引用
    
    print("\n" + "=" * 80)
    print("🎯 CodeMind 数据库初始化脚本")
    print("=" * 80)
    
    # 步骤 1：启动 Docker 服务
    if not start_docker_services():
        sys.exit(1)
    
    # 步骤 2：等待服务就绪
    if not wait_for_services():
        print("\n❌ 服务启动失败，请检查 Docker 日志")
        sys.exit(1)
    
    # 步骤 3：测试 PostgreSQL
    if not test_postgresql():
        sys.exit(1)
    
    # 步骤 4：测试 Milvus
    if not test_milvus():
        sys.exit(1)
    
    print("\n" + "=" * 80)
    print("✅ 数据库初始化完成！")
    print("=" * 80)
    print("\n📊 服务访问地址:")
    print("   - PostgreSQL: localhost:5432")
    print("   - Milvus: localhost:19530")
    print("   - Redis: localhost:6379")
    print("   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)")
    print("\n🎉 可以开始使用了！")


if __name__ == "__main__":
    main()
