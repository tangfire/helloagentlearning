#!/bin/bash

# ==========================================
# WSL2 中快速启动 Docker 容器的脚本
# ==========================================

set -e

echo "=========================================="
echo "🚀 CodeMind Docker 容器快速启动脚本"
echo "=========================================="

# 检查 Docker 是否运行
if ! sudo service docker status > /dev/null 2>&1; then
    echo "⚠️  Docker 未运行，正在启动..."
    sudo service docker start
    sleep 3
fi

echo "✅ Docker 服务已启动"

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 项目目录：$SCRIPT_DIR"

# 检查 docker-compose.yml 是否存在
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ 错误：docker-compose.yml 不存在"
    exit 1
fi

# 停止旧的容器（如果有）
echo ""
echo "🛑 停止可能存在的旧容器..."
docker-compose down 2>/dev/null || true

# 启动所有容器
echo ""
echo "🎯 启动 Docker 容器..."
docker-compose up -d

# 等待容器启动
echo ""
echo "⏳ 等待容器启动..."
sleep 5

# 检查容器状态
echo ""
echo "📊 容器状态："
docker-compose ps

# 检查健康状态
echo ""
echo "🏥 健康检查..."
unhealthy=$(docker-compose ps | grep -c "(unhealthy)" || true)
if [ "$unhealthy" -gt 0 ]; then
    echo "⚠️  有 $unhealthy 个容器未健康，等待 30 秒后重试..."
    sleep 30
    docker-compose ps
fi

echo ""
echo "=========================================="
echo "✅ Docker 容器启动完成！"
echo "=========================================="
echo ""
echo "📱 访问地址:"
echo "   - 前端界面：http://localhost:8000"
echo "   - API 文档：http://localhost:8000/docs"
echo ""
echo "💡 下一步操作:"
echo "   1. 在 Windows 中测试数据库连接:"
echo "      python test_database_connection.py"
echo ""
echo "   2. 启动 Web 应用:"
echo "      python start_web_app.py"
echo ""
echo "   3. 查看容器日志:"
echo "      docker-compose logs -f"
echo ""
echo "=========================================="
