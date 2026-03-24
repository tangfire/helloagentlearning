# 快速开始指南

本文档帮助你快速搭建和运行 CodeMind 智能代码助手。

## 📋 前置要求

### 必需软件
- **Python 3.10+** 
- **Docker & Docker Compose** (用于快速部署数据库)

### 可选软件
- **PostgreSQL 15+** (本地安装，带 pgvector 扩展)
- **Milvus 2.x** (本地安装)

## 🚀 方式一：使用 Docker Compose（推荐）

### 步骤 1: 安装依赖

```bash
cd helloagentlearning
pip install -r requirements.txt
```

### 步骤 2: 配置环境变量

编辑 `01_hello_agent/.env` 文件：

```env
# LLM API 配置
OPENAI_API_KEY=your_api_key_here
MODEL=gpt-4o-mini
BASE_URL=https://api.openai-proxy.org/v1

# 数据库配置（默认即可）
POSTGRES_USER=codemind
POSTGRES_PASSWORD=codemind2024
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=codemind

# Milvus 配置（默认即可）
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### 步骤 3: 启动数据库服务

```bash
cd CodeMind

# Windows PowerShell
.\start_docker.ps1

# Linux/Mac
./start_docker_wsl.sh

# 或手动执行
docker-compose up -d
```

### 步骤 4: 验证服务启动

```bash
# 等待 2-3 分钟后检查服务状态
docker-compose ps

# 应该看到以下服务都处于 Up 状态：
# - CodeMind-postgres-1
# - CodeMind-milvus-standalone
# - CodeMind-etcd
# - CodeMind-minio
# - CodeMind-redis
```

### 步骤 5: 初始化数据库

```bash
python init_database.py
```

如果成功，你会看到：
```
✅ 数据库连接成功
✅ 表结构创建完成
✅ 默认用户已创建：admin
```

### 步骤 6: 启动 Web 应用

```bash
# 方式 1: 使用启动脚本（推荐）
python start_web_app.py

# 方式 2: 直接运行 uvicorn
cd web_app
uvicorn web_api:app --reload --host 0.0.0.0 --port 8000
```

### 步骤 7: 访问应用

打开浏览器访问：**http://localhost:8000**

🎉 完成！你现在可以：
- 创建工作空间
- 上传文档
- 开始智能问答

---

## 🔧 方式二：本地安装数据库

如果你不想使用 Docker，可以本地安装 PostgreSQL 和 Milvus。

### PostgreSQL 安装

1. **下载并安装 PostgreSQL 15+**
   - https://www.postgresql.org/download/

2. **安装 pgvector 扩展**
   ```bash
   # Windows: 使用 Stack Builder
   # Linux: 
   sudo apt install postgresql-15-pgvector
   
   # macOS:
   brew install pgvector
   ```

3. **启用扩展**
   ```sql
   CREATE EXTENSION vector;
   ```

### Milvus 安装

参考官方文档：https://milvus.io/docs/install_standalone-docker.md

### 配置连接

编辑 `.env` 文件，指向你的本地数据库：

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

---

## 🧪 测试安装

### 测试数据库连接

```bash
# 测试 PostgreSQL
psql -h localhost -U codemind -d codemind

# 在 psql 中执行
\dt  # 查看所有表
SELECT * FROM users;  # 查看默认用户
```

### 测试 Milvus 连接

```python
# test_milvus.py
from pymilvus import connections, utility

connections.connect(host="localhost", port=19530)
print(f"Milvus 版本：{utility.get_server_version()}")
print(f"集合列表：{utility.list_collections()}")
```

### 运行完整测试

```bash
cd tests
python test_web_api.py
```

---

## ❓ 常见问题

### Q1: Docker Compose 命令未找到

**错误**: `docker-compose: command not found`

**解决**: 使用新版本的命令（注意中间没有横杠）：
```bash
docker compose up -d
```

### Q2: 端口被占用

**错误**: `Bind for 0.0.0.0:5432 failed: port is already allocated`

**解决**:
```bash
# Windows: 查找并停止占用进程
netstat -ano | findstr :5432
taskkill /PID <PID> /F

# 或修改 docker-compose.yml 中的端口映射
ports:
  - "5433:5432"  # 将外部端口改为 5433
```

### Q3: Milvus 启动失败

**症状**: Milvus 容器反复重启

**解决**:
```bash
# 增加内存限制（编辑 docker-compose.yml）
services:
  milvus-standalone:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Q4: pgvector 扩展不存在

**错误**: `ERROR: extension "vector" does not exist`

**解决**: 确保使用正确的 PostgreSQL 镜像（已在 docker-compose.yml 中配置为 `pgvector/pgvector:pg16`）

---

## 📊 验证清单

完成后，你应该能够确认：

- [ ] PostgreSQL 正常运行并可连接
- [ ] Milvus 正常运行并可连接
- [ ] 数据库表结构已创建（8 张表）
- [ ] 默认用户 `admin` 已创建
- [ ] Web 应用可访问（http://localhost:8000）
- [ ] 可以创建工作空间
- [ ] 可以上传文件
- [ ] 可以进行智能问答

---

## 🎯 下一步

环境搭建完成后，建议阅读：

1. **[API 指南](docs/API_GUIDE.md)** - 了解所有可用的 API 接口
2. **[开发指南](docs/DEVELOPMENT_GUIDE.md)** - 深入了解代码结构和扩展方法
3. **[数据库指南](docs/DATABASE_GUIDE.md)** - 学习数据库架构和优化技巧

## 💡 使用技巧

### 创建工作空间
```bash
curl -X POST http://localhost:8000/api/workspace/create \
  -H "Content-Type: application/json" \
  -d '{"name":"我的项目","description":"测试"}'
```

### 上传文件
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "files=@document.pdf"
```

### 发送问题
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"项目结构是什么？"}'
```

---

## 🆘 获取帮助

如果遇到其他问题：

1. 查看日志文件：
   ```bash
   docker-compose logs -f
   ```

2. 检查 `.env` 配置是否正确

3. 重启所有服务：
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. 提交 Issue 到项目仓库

祝你使用愉快！🚀
