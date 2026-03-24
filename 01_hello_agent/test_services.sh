#!/bin/bash

echo "=========================================="
echo "🧪 CodeMind 数据库连接测试"
echo "=========================================="

# 等待服务启动
echo ""
echo "⏳ 等待 30 秒让服务启动..."
sleep 30

# 测试 PostgreSQL
echo ""
echo "📊 测试 PostgreSQL..."
if command -v psql &> /dev/null; then
    PGPASSWORD=codemind2024 psql -h localhost -U codemind -d codemind -c "SELECT version();" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "✅ PostgreSQL 连接成功"
        
        # 查询表数量
        TABLE_COUNT=$(PGPASSWORD=codemind2024 psql -h localhost -U codemind -d codemind -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null)
        echo "   📊 数据表数量：$TABLE_COUNT"
    else
        echo "❌ PostgreSQL 连接失败"
    fi
else
    echo "⚠️  psql 命令未安装，跳过测试"
fi

# 测试 Milvus
echo ""
echo "🔍 测试 Milvus..."
if command -v curl &> /dev/null; then
    MILVUS_HEALTH=$(curl -s http://localhost:9091/healthz 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "✅ Milvus 健康检查通过"
        echo "   响应：$MILVUS_HEALTH"
    else
        echo "❌ Milvus 连接失败"
    fi
else
    echo "⚠️  curl 命令未安装，跳过测试"
fi

# 测试 Redis
echo ""
echo "📦 测试 Redis..."
if command -v redis-cli &> /dev/null; then
    REDIS_PING=$(redis-cli -h localhost ping 2>/dev/null)
    if [ "$REDIS_PING" = "PONG" ]; then
        echo "✅ Redis 连接成功"
    else
        echo "❌ Redis 连接失败"
    fi
else
    echo "⚠️  redis-cli 命令未安装，跳过测试"
fi

# Docker 容器状态
echo ""
echo "🐳 Docker 容器状态:"
docker compose ps

echo ""
echo "=========================================="
echo "✅ 测试完成"
echo "=========================================="
