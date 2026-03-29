# 🚀 快速启动指南 - 企业 RAG 知识库与 PPT 诊断报告生成平台

## ⚡ 三步快速启动

### 前提条件检查

确保以下服务已在 **WSL2 Docker** 中运行：

```bash
# 在 WSL2 中执行
docker ps
```

应该看到：
- ✅ PostgreSQL 容器（端口 5432）
- ✅ Milvus 容器（端口 19530）

如果未运行，请参考项目的 `docker-compose.yml` 启动服务。

---

## 📋 Windows 主机快速启动

### 方式一：使用启动脚本（推荐）

```powershell
.\start.ps1
```

然后在菜单中选择：
1. **首次使用** → 选择 `1` 执行数据库迁移
2. **安装依赖** → 选择 `2` 安装 Python 包
3. **启动服务** → 选择 `3` 启动 Web 服务器

### 方式二：手动启动

#### 1. 激活虚拟环境（如果使用）
```powershell
.venv\Scripts\Activate.ps1
```

#### 2. 执行数据库迁移
```powershell
python CodeMind/migrate_database.py
```

**注意**：此步骤需要 PostgreSQL 数据库已运行并可访问。

#### 3. 安装依赖
```powershell
pip install -r requirements.txt
```

#### 4. 启动 Web 服务
```powershell
python CodeMind/web_app/start_web_app.py
```

或者使用 uvicorn：
```powershell
cd CodeMind\web_app
uvicorn web_api:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🌐 访问地址

启动成功后，打开浏览器访问：

- **原有代码助手界面**: http://localhost:8000
- **🆕 企业诊断平台**: http://localhost:8000/enterprise
- **API 文档**: http://localhost:8000/docs

---

## 💻 使用示例

### 场景：为 A 公司生成管理诊断报告

#### 1. 创建企业档案
访问 http://localhost:8000/enterprise

- 点击左侧 "📋 企业列表"
- 点击 "➕ 创建企业"
- 填写信息：
  - 企业名称：A 科技有限公司
  - 企业编码：A-TECH-2026
  - 所属行业：信息技术
  - 企业规模：中型
  - 企业描述：专注于软件开发和 IT 服务

#### 2. 添加企业知识
- 切换到 "📚 知识库" 标签
- 点击 "📝 添加知识"
- 选择刚创建的 A 公司
- 填写知识内容，例如：
  ```
  标题：A 公司 2025 年度财务报告
  分类：财务
  文档类型：报告
  内容：[粘贴财务报告摘要]
  ```

重复以上步骤，添加更多企业资料：
- 组织架构图
- 人力资源数据
- 业务流程文档
- 市场分析

#### 3. 生成诊断报告
- 切换到 "📊 报告管理" 标签
- 点击 "📊 生成报告"
- 配置报告参数：
  - 选择企业：A 科技有限公司
  - 报告标题：A 公司 2026 年度管理诊断报告
  - 分析要求：请全面分析公司的经营状况、存在问题并提出改进建议
  - ☑️ 同时生成 PPT 演示文稿

- 点击 "生成报告"，等待 2-5 分钟

#### 4. 查看结果
报告生成后，系统会显示：
- ✅ 报告生成成功
- 📄 完整的分析内容
- 📋 结 论列表
- 💡 改进建议
- 📽️ PPT 文件路径

PPT 文件保存在：`CodeMind/tools/output/reports/` 目录

---

## 🔧 常见问题解决

### Q1: 数据库连接失败
**错误信息**: `connection to server at "localhost" failed`

**解决方案**:
1. 确认 WSL2 中的 Docker 容器已启动
2. 在 WSL2 中执行：`docker ps` 查看容器状态
3. 如果容器未运行，使用 docker-compose 启动：
   ```bash
   # 在 WSL2 中
   cd /path/to/project
   docker-compose up -d
   ```

### Q2: 找不到迁移文件
**错误信息**: `迁移目录不存在`

**解决方案**:
检查当前工作目录是否正确：
```powershell
# 应该在项目根目录
pwd
# 输出应该是：D:\GitRespority\helloagentlearning

# 然后执行
python CodeMind/migrate_database.py
```

### Q3: PPT 生成失败
**错误信息**: `未安装 python-pptx 库`

**解决方案**:
```powershell
pip install python-pptx
```

### Q4: 导入模块错误
**错误信息**: `ModuleNotFoundError`

**解决方案**:
确保安装了所有依赖：
```powershell
pip install -r requirements.txt
```

---

## 📊 API 测试示例

使用 curl 或 Postman 测试 API：

### 创建企业
```bash
curl -X POST http://localhost:8000/api/enterprise/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "测试企业",
    "code": "TEST-001",
    "industry": "制造业",
    "scale": "medium"
  }'
```

### 添加知识
```bash
curl -X POST http://localhost:8000/api/knowledge/add \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise_id": "企业 ID",
    "title": "测试文档",
    "content": "文档内容",
    "category": "财务"
  }'
```

### 生成报告
```bash
curl -X POST http://localhost:8000/api/report/generate \
  -H "Content-Type: application/json" \
  -d '{
    "enterprise_id": "企业 ID",
    "title": "测试报告",
    "generate_ppt": true
  }'
```

---

## 🎯 下一步

完成快速启动后，建议：

1. 📖 阅读完整文档：`UPGRADE_GUIDE.md`
2. 📊 了解项目详情：`PROJECT_UPGRADE_SUMMARY.md`
3. 🔍 探索 API 文档：http://localhost:8000/docs
4. 💡 尝试不同场景：企业管理咨询、投资尽调、内部审计等

---

## 📞 获取帮助

如遇到问题：

1. 查看控制台输出的详细错误信息
2. 检查日志文件
3. 参考完整文档 `UPGRADE_GUIDE.md`
4. 访问 API 文档查看接口说明

---

**祝您使用愉快！** 🎉

立即开始：`.\start.ps1`
