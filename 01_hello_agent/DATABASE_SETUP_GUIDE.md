# 🚀 数据库架构升级 - 快速开始指南

## 📋 第一步：安装依赖

```bash
cd D:\GitRespority\helloagentlearning
pip install -r requirements.txt
```

**新增的依赖说明**：
- `pymilvus`: Milvus 向量数据库客户端
- `psycopg2-binary`: PostgreSQL 数据库驱动
- `sqlalchemy`: Python ORM 框架
- `fastapi`, `uvicorn`: Web 框架（已有）

---

## 🐳 第二步：启动 Docker 服务

### Windows PowerShell（管理员权限）

```powershell
# 切换到项目目录
cd D:\GitRespority\helloagentlearning\01_hello_agent

# 启动所有服务（后台运行）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 如果需要停止服务
docker-compose down

# 如果需要完全清理（删除数据卷）
docker-compose down -v
```

---

## 🔍 第三步：验证服务启动

### 等待服务就绪（约 2-3 分钟）

```powershell
# 检查 PostgreSQL
curl http://localhost:5432

# 检查 Milvus（浏览器访问）
http://localhost:9091/healthz

# 检查 Redis
redis-cli ping
```

### 或使用 Docker 命令查看日志

```powershell
# 查看所有服务日志
docker-compose logs -f

# 查看单个服务日志
docker-compose logs postgres
docker-compose logs milvus-standalone
docker-compose logs redis
```

---

## 🧪 第四步：测试数据库连接

### 测试 PostgreSQL

```bash
# 方法 1：使用 psql 命令行
docker exec -it 01_hello_agent-postgres-1 psql -U codemind -d codemind

# 执行 SQL 查询
\dt  # 查看所有表
SELECT * FROM users;  # 查看默认用户
```

### 测试 Milvus

```python
# 创建 test_milvus.py
from pymilvus import connections, utility

# 连接 Milvus
connections.connect(host="localhost", port=19530)

# 检查连接
print(f"Milvus 版本：{utility.get_server_version()}")

# 列出所有集合
print(f"集合列表：{utility.list_collections()}")
```

### 测试 PostgreSQL（Python）

```python
# 创建 test_postgres.py
from sqlalchemy import create_engine, text

# 数据库连接 URL
DATABASE_URL = "postgresql://codemind:codemind2024@localhost:5432/codemind"

# 创建引擎
engine = create_engine(DATABASE_URL)

# 测试连接
with engine.connect() as conn:
    result = conn.execute(text("SELECT version()"))
    print(f"PostgreSQL 版本：{result.scalar()}")
    
    # 查询表
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """))
    tables = [row[0] for row in result]
    print(f"数据表列表：{tables}")
```

---

## 📊 第五步：查看数据库结构

### PostgreSQL 表结构

```sql
-- 查看所有表
\dt

-- 查看 users 表结构
\d users

-- 查看 documents 表结构
\d documents

-- 查看 document_chunks 表（带向量）
\d document_chunks

-- 查看索引
\di
```

### Milvus 集合

```python
from pymilvus import connections, Collection, utility

connections.connect(host="localhost", port=19530)

# 列出所有集合
print(utility.list_collections())

# 查看集合详情
collection = Collection("document_chunks")
print(f"集合名称：{collection.name}")
print(f"Schema: {collection.schema}")
print(f"统计信息：{collection.stats}")
```

---

## 🎯 第六步：运行初始化脚本（可选）

如果自动初始化失败，可以手动执行 SQL 脚本：

```bash
# 进入 PostgreSQL 容器
docker exec -it 01_hello_agent-postgres-1 bash

# 执行初始化 SQL
psql -U codemind -d codemind -f /docker-entrypoint-initdb.d/001_init_schema.sql
```

---

## 🛠️ 常见问题排查

### 问题 1：Docker Compose 未找到

**错误**：`docker-compose: command not found`

**解决**：
```bash
# 使用新版本的 Docker Compose（Docker Desktop 自带）
docker compose up -d  # 注意中间没有横杠
```

### 问题 2：端口被占用

**错误**：`Bind for 0.0.0.0:5432 failed: port is already allocated`

**解决**：
```bash
# 查找占用端口的进程
netstat -ano | findstr :5432

# 停止占用进程或修改 docker-compose.yml 中的端口映射
```

### 问题 3：Milvus 启动失败

**症状**：Milvus 容器反复重启

**解决**：
```bash
# 查看详细日志
docker-compose logs milvus-standalone

# 增加内存限制（在 docker-compose.yml 中）
services:
  milvus-standalone:
    deploy:
      resources:
        limits:
          memory: 4G
```

### 问题 4：pgvector 扩展未找到

**错误**：`ERROR: extension "vector" does not exist`

**原因**：使用了错误的 PostgreSQL 镜像

**解决**：确保使用 `pgvector/pgvector:pg16` 镜像（已在 docker-compose.yml 中配置）

---

## 📈 性能优化建议

### PostgreSQL 优化

编辑 `postgresql.conf`（通过 Docker 卷挂载）：
```conf
# 内存配置
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB

# 向量索引优化
ivfflat.probes = 10  # 搜索精度和速度的平衡
```

### Milvus 优化

编辑 `milvus.yaml`（通过 Docker 卷挂载）：
```yaml
indexConfig:
  index:
    nlist: 1024  # 索引块数量
searchConfig:
  nprobe: 32  # 搜索探针数量
```

---

## 🎉 完成标志

当你看到以下输出时，说明一切正常：

✅ **Docker 服务状态**：
```
NAME                        STATUS         PORTS
01_hello_agent-etcd         Up             2379/tcp
01_hello_agent-minio        Up             9000/tcp, 9001/tcp
01_hello_agent-milvus       Up             19530/tcp, 9091/tcp
01_hello_agent-postgres     Up             5432/tcp
01_hello_agent-redis        Up             6379/tcp
```

✅ **PostgreSQL 查询结果**：
```
已创建 8 张表：users, workspaces, documents, document_chunks, 
operation_logs, notes, conversation_history, workspace_stats
```

✅ **Milvus 集合状态**：
```
集合名称：document_chunks
向量维度：1536
索引类型：IVF_FLAT
```

---

## 🚀 下一步

数据库环境搭建完成后，我们将：

1. **重构代码架构**：将 FAISS 迁移到 Milvus + PostgreSQL
2. **实现文档上传流程**：同时写入关系数据库和向量数据库
3. **实现混合查询**：向量相似度 + SQL 条件过滤
4. **添加用户认证**：JWT Token 认证系统
5. **性能测试**：对比 FAISS vs Milvus 的性能差异

敬请期待！🎯
