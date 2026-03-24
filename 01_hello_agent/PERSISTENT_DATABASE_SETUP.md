# 📦 数据库持久化配置指南

本指南帮助你配置项目使用 WSL2 Docker 中的 PostgreSQL 和 Milvus 进行真正的数据持久化存储。

## 🎯 目标

- ✅ PostgreSQL 存储文档元数据、用户信息、工作空间等业务数据
- ✅ Milvus 存储向量数据（用于相似度搜索）
- ✅ Redis 提供缓存支持
- ✅ 数据持久化到 Docker volumes，重启不丢失

---

## 📋 前置条件

1. **WSL2 已安装并配置好**
2. **Docker Desktop for Windows 已安装**，并且：
   - 启用了 WSL2 后端
   - 在 WSL2 中可以使用 `docker` 命令

---

## 🚀 快速开始

### 第一步：启动 Docker 容器

```bash
# 1. 打开 PowerShell 或终端，进入 WSL2
wsl

# 2. 启动 Docker 服务（如果未启动）
sudo service docker start

# 3. 进入项目目录（WSL2 路径）
cd /mnt/d/GitRespority/helloagentlearning/01_hello_agent

# 4. 启动所有容器（后台运行）
docker-compose up -d

# 5. 查看容器状态
docker ps
```

**预期输出：**
```
CONTAINER ID   IMAGE                               STATUS         PORTS
xxxx           quay.io/coreos/etcd:v3.5.5          Up (healthy)   2379/tcp
xxxx           minio/minio:RELEASE.2023-03-20...   Up (healthy)   9000/tcp, 9001/tcp
xxxx           milvusdb/milvus:v2.3.0              Up (healthy)   19530/tcp, 9091/tcp
xxxx           pgvector/pgvector:pg16              Up (healthy)   5432/tcp
xxxx           redis:7-alpine                      Up (healthy)   6379/tcp
```

### 第二步：验证数据库连接

在 Windows 的 PowerShell 中运行：

```powershell
cd D:\GitRespority\helloagentlearning\01_hello_agent
python test_database_connection.py
```

**预期输出：**
```
🐘 测试 PostgreSQL 连接
✅ PostgreSQL 版本：PostgreSQL 16.x ...
✅ 数据库表已创建：8 个表
   - documents
   - document_chunks
   - users
   - workspaces
   ...

🔷 测试 Milvus 向量数据库连接
✅ Milvus 集合统计：
   - 集合名称：document_chunks
   - 向量数量：0

🔴 测试 Redis 缓存连接
✅ Redis 连接成功：localhost:6379
✅ Redis 读写测试：test_value

📊 测试结果汇总
PostgreSQL: ✅ 正常
Milvus:     ✅ 正常
Redis:      ✅ 正常

🎉 所有数据库连接正常！可以开始使用持久化存储了。
```

### 第三步：初始化数据库（如果需要）

如果第二步显示"数据库中没有表"，需要运行初始化脚本：

```powershell
python init_database.py
```

### 第四步：启动 Web 应用

```powershell
python .\start_web_app.py
```

访问前端：http://localhost:8000

---

## 📁 数据持久化说明

### Docker Volumes

所有数据都存储在 Docker volumes 中，位置：

```
\\wsl$\docker-desktop-data\data\docker\volumes\
```

主要 volumes：

| Volume Name    | 用途                  | 对应服务   |
|----------------|-----------------------|------------|
| postgres_data  | PostgreSQL 数据文件   | PostgreSQL |
| milvus_data    | Milvus 向量数据       | Milvus     |
| milvus_etcd    | Milvus 元数据         | etcd       |
| milvus_minio   | Milvus 对象存储       | MinIO      |
| redis_data     | Redis 持久化数据      | Redis      |

### 数据不会丢失

即使你：
- ✅ 停止容器：`docker-compose down`
- ✅ 重启 WSL2
- ✅ 重启电脑

数据都会保留在 Docker volumes 中。下次启动容器时会自动加载。

### 如果要完全清空数据

```bash
# 停止并删除所有容器和 volumes
docker-compose down -v

# 重新启动
docker-compose up -d
```

⚠️ **警告：这会删除所有数据！**

---

## 🔧 配置文件说明

### .env 文件

```env
# PostgreSQL 配置
POSTGRES_USER=codemind
POSTGRES_PASSWORD=codemind2024
POSTGRES_HOST=localhost      # WSL2 中通过 localhost 访问
POSTGRES_PORT=5432
POSTGRES_DB=codemind

# Milvus 配置
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379

# 启用数据库增强版（重要！）
USE_DATABASE_ENHANCED=True
```

### web_api.py 配置

确保以下配置为 `True`：

```python
USE_DATABASE_ENHANCED = True  # True=PostgreSQL + Milvus, False=FAISS（内存模式）
```

---

## 🛠️ 常用 Docker 命令

### 查看容器状态

```bash
docker ps
docker-compose ps
```

### 查看日志

```bash
# 查看所有容器日志
docker-compose logs -f

# 查看特定容器日志
docker-compose logs postgres
docker-compose logs milvus-standalone
```

### 重启容器

```bash
# 重启所有容器
docker-compose restart

# 重启单个容器
docker-compose restart postgres
```

### 停止容器

```bash
docker-compose down
```

### 进入容器内部

```bash
# 进入 PostgreSQL
docker exec -it 01_hello_agent-postgres-1 psql -U codemind -d codemind

# 进入 Milvus
docker exec -it 01_hello_agent-milvus-standalone-1 bash
```

---

## 📊 数据库结构

### PostgreSQL 表

- **users**: 用户信息
- **workspaces**: 工作空间
- **documents**: 文档元数据
- **document_chunks**: 文档分块
- **conversation_history**: 对话历史
- **operation_logs**: 操作日志
- **notes**: 笔记/任务

### Milvus 集合

- **document_chunks**: 向量数据（与 PostgreSQL 的 document_chunks 关联）

---

## ❓ 常见问题

### Q1: Docker 容器启动失败？

**A:** 检查 WSL2 和 Docker 是否正常：

```bash
# 检查 Docker 是否运行
sudo service docker status

# 启动 Docker
sudo service docker start

# 检查容器是否冲突
docker ps -a
docker-compose down
docker-compose up -d
```

### Q2: 无法连接到数据库？

**A:** 检查网络和端口：

```bash
# 在 WSL2 中检查端口
netstat -tlnp | grep 5432
netstat -tlnp | grep 19530

# 在 Windows 中测试连接
telnet localhost 5432
telnet localhost 19530
```

### Q3: 数据会同步到 WSL2 吗？

**A:** 不会。数据存储在 Docker volumes 中，与 WSL2 文件系统分离。即使 WSL2 被重置，数据也会保留。

### Q4: 如何在备份数据？

**A:** 备份 Docker volumes：

```bash
# 导出 volume
docker run --rm -v helloagent_milvus_data:/data -v $(pwd):/backup ubuntu tar czf /backup/milvus_backup.tar.gz -C /data .

# 导入 volume
docker run --rm -v helloagent_milvus_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/milvus_backup.tar.gz -C /data
```

---

## 🎯 下一步

配置完成后，你可以：

1. ✅ 启动 Web 应用：`python start_web_app.py`
2. ✅ 访问前端：http://localhost:8000
3. ✅ 创建工作空间
4. ✅ 上传文档（PDF、代码等）
5. ✅ 智能问答（基于持久化的向量数据）

所有上传的文档和生成的向量都会永久保存在数据库中！

---

## 📞 获取帮助

如果有问题，请检查：

1. `.env` 文件配置是否正确
2. Docker 容器是否正常运行
3. 运行 `python test_database_connection.py` 测试连接
4. 查看容器日志：`docker-compose logs -f`
