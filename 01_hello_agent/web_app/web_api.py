"""
CodeMind Web API - FastAPI 后端

提供完整的 RESTful API，支持：
- 智能问答（Chat）
- 代码库操作（Codebase）
- 任务管理（Tasks）
- MCP 服务控制（MCP）
- 文档处理（Documents）
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import json
from pathlib import Path
from datetime import datetime
import uvicorn

# 导入 CodeMind 核心组件
import sys
from pathlib import Path as PathLib

# 添加项目根目录到路径
project_root = PathLib(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.codemind_assistant import CodeMindAssistant
from core.codemind_assistant_db import CodeMindAssistantDB  # 新增：数据库增强版
from tools.mcp_client import MCPClient

# ==================== 基础路径定义 ====================

# 获取当前文件所在目录
BASE_DIR = Path(__file__).parent

# 用户数据目录 - 与项目分离，存储所有工作空间数据
# Windows: D:\CodeMindData 或 用户目录下的 CodeMindData
USER_DATA_DIR = PathLib.home() / "CodeMindData"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
print(f"📁 用户数据目录：{USER_DATA_DIR}")

# ==================== FastAPI 应用初始化 ====================

app = FastAPI(
    title="CodeMind Assistant API",
    description="代码库智能维护助手 - Web API",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 全局状态 ====================

# 工作空间管理器
class WorkspaceManager:
    """管理多个工作空间"""
    def __init__(self, base_path: Path):
        self.base_path = base_path / "workspaces"
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.workspaces: Dict[str, dict] = {}  # workspace_id -> info
        self.current_workspace_id: Optional[str] = None
        
        # 启动时加载已有的工作空间
        self._load_workspaces()
    
    def _load_workspaces(self):
        """从磁盘加载已有的工作空间"""
        if not self.base_path.exists():
            return
        
        for workspace_dir in self.base_path.iterdir():
            if workspace_dir.is_dir():
                workspace_id = workspace_dir.name
                config_file = workspace_dir / "config.json"
                
                if config_file.exists():
                    import json
                    with open(config_file, 'r', encoding='utf-8') as f:
                        workspace_data = json.load(f)
                        self.workspaces[workspace_id] = workspace_data
                        print(f"📁 加载工作空间：{workspace_data['name']} (ID: {workspace_id})")
        
    def create_workspace(self, name: str, description: str = "") -> str:
        """创建工作空间"""
        import uuid
        import json
        
        workspace_id = str(uuid.uuid4())[:8]
        workspace_path = self.base_path / workspace_id
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (workspace_path / "documents").mkdir(exist_ok=True)
        (workspace_path / "vectorstore").mkdir(exist_ok=True)
        (workspace_path / "sessions").mkdir(exist_ok=True)
        
        workspace_info = {
            "id": workspace_id,
            "name": name,
            "description": description,
            "path": str(workspace_path),
            "created_at": datetime.now().isoformat(),
            "document_count": 0,
            "session_count": 0
        }
        
        # 保存配置到文件（持久化）
        config_file = workspace_path / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(workspace_info, f, ensure_ascii=False, indent=2)
        
        self.workspaces[workspace_id] = workspace_info
        
        print(f"✅ 创建工作空间：{name} (ID: {workspace_id})")
        return workspace_id
    
    def switch_workspace(self, workspace_id: str) -> bool:
        """切换工作空间"""
        if workspace_id in self.workspaces:
            self.current_workspace_id = workspace_id
            print(f"🔄 切换到工作空间：{self.workspaces[workspace_id]['name']}")
            return True
        return False
    
    def delete_workspace(self, workspace_id: str) -> bool:
        """删除工作空间"""
        if workspace_id in self.workspaces:
            import shutil
            workspace_path = Path(self.workspaces[workspace_id]["path"])
            if workspace_path.exists():
                shutil.rmtree(workspace_path)
            del self.workspaces[workspace_id]
            if self.current_workspace_id == workspace_id:
                self.current_workspace_id = None
            return True
        return False
    
    def get_current_workspace(self) -> Optional[dict]:
        """获取当前工作空间"""
        if self.current_workspace_id and self.current_workspace_id in self.workspaces:
            return self.workspaces[self.current_workspace_id]
        return None
    
    def list_workspaces(self) -> List[dict]:
        """列出所有工作空间"""
        return list(self.workspaces.values())

# 会话管理器
class SessionManager:
    """管理对话会话"""
    def __init__(self):
        self.sessions: Dict[str, list] = {}  # session_id -> messages
        
    def save_session(self, workspace_id: str, session_name: str, messages: list) -> str:
        """保存会话"""
        import json
        import uuid
        from pathlib import Path as PathLib
        
        session_id = str(uuid.uuid4())[:8]
        workspace_info = workspace_manager.get_current_workspace()
        if not workspace_info:
            raise Exception("没有活跃的工作空间")
        
        session_path = PathLib(workspace_info["path"]) / "sessions" / f"{session_id}.json"
        
        session_data = {
            "id": session_id,
            "name": session_name,
            "workspace_id": workspace_info["id"],
            "messages": messages,
            "created_at": datetime.now().isoformat()
        }
        
        with open(session_path, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 保存会话：{session_name}")
        return session_id
    
    def load_sessions(self, workspace_id: str) -> List[dict]:
        """加载工作空间的所有会话"""
        import json
        from pathlib import Path as PathLib
        
        workspace_info = self.workspaces.get(workspace_id)
        if not workspace_info:
            return []
        
        sessions_path = PathLib(workspace_info["path"]) / "sessions"
        if not sessions_path.exists():
            return []
        
        sessions = []
        for session_file in sessions_path.glob("*.json"):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                    sessions.append(session_data)
            except Exception as e:
                print(f"⚠️  加载会话失败 {session_file.name}: {e}")
        
        return sorted(sessions, key=lambda x: x.get('created_at', ''), reverse=True)

# 初始化工作空间管理器
workspace_manager = WorkspaceManager(USER_DATA_DIR)
session_manager = SessionManager()

# 全局配置：是否使用数据库增强版
USE_DATABASE_ENHANCED = True  # True=PostgreSQL + Milvus, False=FAISS（内存模式）

# 单例助手实例（每个工作空间一个）
assistants: Dict[str, CodeMindAssistant] = {}  # workspace_id -> assistant
assistants_db: Dict[str, CodeMindAssistantDB] = {}  # workspace_id -> assistant_db

# WebSocket 连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        """广播消息到所有连接的客户端"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        """发送个人消息"""
        await websocket.send_json(message)

manager = ConnectionManager()

# ==================== Pydantic 模型 ====================

class WorkspaceCreate(BaseModel):
    """创建工作空间"""
    name: str
    description: str = ""

class WorkspaceSwitch(BaseModel):
    """切换工作空间"""
    workspace_id: str

class ChatRequest(BaseModel):
    question: str
    use_mqe: bool = True
    use_hyde: bool = True
    use_context: bool = True

class ChatResponse(BaseModel):
    answer: str
    sources: List[Any] = []  # 源文档信息列表
    confidence: float = 0.8
    retrieval_method: str = "hybrid"
    context_used: bool = True
    workspace_id: str = ""

class CodebaseRequest(BaseModel):
    command: str = "dir"
    save_to_notes: bool = False

class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    tags: Optional[List[str]] = None

class TaskUpdate(BaseModel):
    status: str
    comment: Optional[str] = None

class DocumentLoadRequest(BaseModel):
    file_path: str

class MCPConnectRequest(BaseModel):
    server_name: str
    command: Optional[str] = None
    args: Optional[List[str]] = None

class MCPToolCallRequest(BaseModel):
    server_name: str
    tool_name: str
    arguments: Dict[str, Any]

class SessionSave(BaseModel):
    """保存会话"""
    workspace_id: str
    session_name: str

def get_assistant() -> CodeMindAssistant:
    """获取或创建助手实例（基于当前工作空间）- 向后兼容"""
    current_workspace = workspace_manager.get_current_workspace()
    if not current_workspace:
        # 如果没有工作空间，创建一个默认的
        print("⚠️  没有活跃工作空间，创建默认工作空间...")
        workspace_id = workspace_manager.create_workspace("默认工作空间", "系统自动创建")
        workspace_manager.switch_workspace(workspace_id)
        current_workspace = workspace_manager.get_current_workspace()
    
    workspace_id = current_workspace["id"]
    
    if workspace_id not in assistants:
        # 初始化助手，指定要维护的项目路径
        assistants[workspace_id] = CodeMindAssistant(
            user_id="web_user",
            project_path=Path(current_workspace["path"])
        )
        
        print(f"🤖 为工作空间 {current_workspace['name']} 初始化助手...")
        
        # 尝试加载已保存的向量索引
        asst = assistants[workspace_id]
        loaded = asst.load_vectorstore()
        
        if not loaded:
            print(f"📂 工作空间 '{current_workspace['name']}' 还没有索引，请先上传文件...")
    
    return assistants[workspace_id]


def get_assistant_db() -> CodeMindAssistantDB:
    """获取或创建数据库增强版助手实例"""
    current_workspace = workspace_manager.get_current_workspace()
    if not current_workspace:
        # 如果没有工作空间，创建一个默认的
        print("⚠️  没有活跃工作空间，创建默认工作空间...")
        workspace_id = workspace_manager.create_workspace("默认工作空间", "系统自动创建")
        workspace_manager.switch_workspace(workspace_id)
        current_workspace = workspace_manager.get_current_workspace()
    
    workspace_id = current_workspace["id"]
    
    if workspace_id not in assistants_db:
        # 初始化数据库版助手
        assistants_db[workspace_id] = CodeMindAssistantDB(
            user_id="admin",  # 使用默认管理员用户
            workspace_id=workspace_id
        )
        
        print(f"🤖 [DB] 为工作空间 {current_workspace['name']} 初始化数据库助手...")
    
    return assistants_db[workspace_id]

# ==================== API 路由 ====================

@app.get("/")
async def root():
    """根路径 - 返回前端页面"""
    html_path = BASE_DIR / "static" / "index.html"
    print(f"📄 请求根路径，HTML 文件位置：{html_path}")
    print(f"📄 文件是否存在：{html_path.exists()}")
    if not html_path.exists():
        raise HTTPException(status_code=404, detail=f"index.html not found at {html_path}")
    return FileResponse(html_path)

@app.get("/api/health")
async def health_check():
    """健康检查"""
    current_ws = workspace_manager.get_current_workspace()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "assistant_initialized": len(assistants) > 0,
        "workspace_count": len(workspace_manager.workspaces),
        "current_workspace": current_ws["name"] if current_ws else None
    }

# ==================== 工作空间管理 API ====================

@app.post("/api/workspace/create")
async def create_workspace(request: WorkspaceCreate):
    """创建工作空间"""
    try:
        workspace_id = workspace_manager.create_workspace(
            name=request.name,
            description=request.description
        )
        
        # 自动切换到新创建的工作空间
        workspace_manager.switch_workspace(workspace_id)
        
        return {
            "success": True,
            "workspace_id": workspace_id,
            "name": request.name,
            "message": f"工作空间 '{request.name}' 已创建"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workspace/list")
async def list_workspaces():
    """列出所有工作空间"""
    try:
        workspaces = workspace_manager.list_workspaces()
        current_id = workspace_manager.current_workspace_id
        
        return {
            "workspaces": workspaces,
            "current_workspace_id": current_id,
            "count": len(workspaces)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workspace/switch")
async def switch_workspace(request: WorkspaceSwitch):
    """切换工作空间"""
    try:
        success = workspace_manager.switch_workspace(request.workspace_id)
        
        if success:
            current_ws = workspace_manager.get_current_workspace()
            # 初始化该工作空间的助手
            get_assistant()
            
            return {
                "success": True,
                "workspace": current_ws,
                "message": f"已切换到工作空间 '{current_ws['name']}'"
            }
        else:
            raise HTTPException(status_code=404, detail="工作空间不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/workspace/delete/{workspace_id}")
async def delete_workspace(workspace_id: str):
    """删除工作空间"""
    try:
        success = workspace_manager.delete_workspace(workspace_id)
        
        if success:
            return {
                "success": True,
                "message": "工作空间已删除"
            }
        else:
            raise HTTPException(status_code=404, detail="工作空间不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 文件上传 API ====================

from fastapi import UploadFile, File
import shutil

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    上传文件到当前工作空间
    
    支持格式：PDF, Word, Excel, PPT, TXT, Markdown, Python 代码等
    """
    import traceback
    from datetime import datetime
    
    try:
        print(f"\n📥 收到上传请求，文件数量：{len(files)}")
        
        current_ws = workspace_manager.get_current_workspace()
        if not current_ws:
            print("❌ 没有活跃的工作空间")
            raise HTTPException(status_code=400, detail="没有活跃的工作空间")
        
        print(f"✅ 当前工作空间：{current_ws['name']} (ID: {current_ws['id']})")
        
        upload_dir = Path(current_ws["path"]) / "documents"
        upload_dir.mkdir(parents=True, exist_ok=True)
        print(f"📂 上传目录：{upload_dir}")
        
        uploaded_files = []
        
        for i, file in enumerate(files):
            print(f"\n📄 处理文件 {i+1}/{len(files)}: {file.filename}")
            print(f"   - 类型：{file.content_type}")
            print(f"   - 大小：{file.size} bytes")
            
            # 解决文件覆盖问题：添加时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_parts = file.filename.rsplit('.', 1)
            if len(filename_parts) == 2:
                new_filename = f"{filename_parts[0]}_{timestamp}.{filename_parts[1]}"
            else:
                new_filename = f"{file.filename}_{timestamp}"
            
            # 保存文件
            file_path = upload_dir / new_filename
            print(f"   - 保存路径：{file_path}")
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            uploaded_files.append({
                "original_filename": file.filename,
                "saved_filename": new_filename,
                "size": file.size,
                "content_type": file.content_type,
                "path": str(file_path)
            })
            print(f"   ✅ 保存成功")
        
        print(f"\n✅ 上传 {len(uploaded_files)} 个文件到工作空间 '{current_ws['name']}'")
        
        # 根据配置选择索引方式
        if USE_DATABASE_ENHANCED:
            # 使用数据库增强版
            asst = get_assistant_db()
            print(f"\n📂 [DB] 开始索引文件到 PostgreSQL + Milvus...")
            
            success_count = 0
            errors = []
            for file_info in uploaded_files:
                try:
                    result = asst.upload_document(
                        file_path=file_info["path"],
                        filename=file_info["original_filename"]
                    )
                    if result:
                        success_count += 1
                    else:
                        errors.append(f"{file_info['original_filename']}: 返回 False")
                except Exception as e:
                    errors.append(f"{file_info['original_filename']}: {str(e)}")
                    print(f"❌ [DB] 文件索引失败 {file_info['original_filename']}: {e}")
                    traceback.print_exc()
            
            if errors:
                error_msg = "\n".join(errors)
                print(f"❌ [DB] 错误详情：{error_msg}")
                raise HTTPException(status_code=500, detail=f"部分文件索引失败:\n{error_msg}")
            
            print(f"✅ [DB] 索引完成：{success_count}/{len(uploaded_files)} 个文件成功")
        else:
            # 使用原有 FAISS 版本
            print(f"\n📂 开始索引工作空间的 documents 目录...")
            asst = get_assistant()
            asst.index_codebase(
                file_patterns=["*"],  # 索引所有文件
                max_files=100
            )
        
        return {
            "success": True,
            "files": uploaded_files,
            "count": len(uploaded_files),
            "workspace_id": current_ws["id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 上传接口发生异常：{e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 会话管理 API ====================

@app.post("/api/session/save")
async def save_session(request: SessionSave):
    """保存当前会话"""
    try:
        # TODO: 需要从 WebSocket 或前端获取当前会话的 messages
        # 这里先实现基本框架
        session_id = session_manager.save_session(
            workspace_id=request.workspace_id,
            session_name=request.session_name,
            messages=[]  # 需要前端传递实际的对话历史
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"会话 '{request.session_name}' 已保存"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/list")
async def list_sessions(workspace_id: str):
    """列出工作空间的所有会话"""
    try:
        sessions = session_manager.load_sessions(workspace_id)
        
        return {
            "sessions": sessions,
            "count": len(sessions),
            "workspace_id": workspace_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/session/load/{session_id}")
async def load_session(session_id: str):
    """加载指定会话"""
    try:
        # TODO: 需要根据 session_id 加载具体的会话数据
        # 这需要改进 SessionManager 的实现
        return {
            "session_id": session_id,
            "messages": []  # 待实现
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    智能问答接口
    
    - **question**: 用户问题
    - **use_mqe**: 是否使用多查询扩展
    - **use_hyde**: 是否使用假设文档嵌入
    - **use_context**: 是否使用历史上下文
    """
    try:
        current_ws = workspace_manager.get_current_workspace()
        
        # 根据配置选择问答方式
        if USE_DATABASE_ENHANCED:
            # 使用数据库增强版
            asst = get_assistant_db()
            result = asst.ask(
                question=request.question,
                use_context=request.use_context
            )
            
            return ChatResponse(
                answer=result["answer"],
                sources=result.get("sources", []),
                confidence=0.8,
                retrieval_method="database_hybrid",
                context_used=result.get("context_used", False),
                workspace_id=current_ws["id"] if current_ws else ""
            )
        else:
            # 使用原有 FAISS 版本
            asst = get_assistant()
            result = asst.ask(
                question=request.question,
                use_mqe=request.use_mqe,
                use_hyde=request.use_hyde,
                use_context=request.use_context
            )
            
            return ChatResponse(
                answer=result["answer"],
                sources=result.get("sources", []),
                confidence=result.get("confidence", 0.8),
                retrieval_method=result.get("retrieval_method", "hybrid"),
                context_used=request.use_context,
                workspace_id=current_ws["id"] if current_ws else ""
            )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 代码库操作 API ====================

@app.post("/api/codebase/explore")
async def explore_codebase(request: CodebaseRequest):
    """探索代码库结构"""
    try:
        asst = get_assistant()
        result = asst.explore_codebase(
            command=request.command,
            save_to_notes=request.save_to_notes
        )
        
        return {
            "success": result["success"],
            "output": result.get("stdout", "") or result.get("stderr", ""),
            "command": request.command
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/codebase/analyze")
async def analyze_file(file_path: str):
    """分析文件"""
    try:
        asst = get_assistant()
        result = asst.analyze_file(file_path)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/codebase/search")
async def search_codebase(pattern: str, file_pattern: str = "*.py"):
    """搜索代码"""
    try:
        asst = get_assistant()
        result = asst.search_in_codebase(pattern, file_pattern)
        return {
            "pattern": pattern,
            "file_pattern": file_pattern,
            "matches": result.get("matches", []),
            "count": len(result.get("matches", []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 任务管理 API ====================

@app.post("/api/tasks/create")
async def create_task(request: TaskCreate):
    """创建任务"""
    try:
        asst = get_assistant()
        task_id = asst.create_task(
            title=request.title,
            description=request.description,
            priority=request.priority,
            tags=request.tags or ["web"]
        )
        
        return {
            "task_id": task_id,
            "title": request.title,
            "status": "created"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/list")
async def list_tasks(status: str = "open", limit: int = 20):
    """列出任务"""
    try:
        asst = get_assistant()
        summary = asst.get_task_summary()
        notes = asst.note_tool.search_notes(status=status)
        
        tasks = [
            {
                "id": note.id,
                "title": note.title,
                "type": note.note_type,
                "priority": note.priority,
                "status": note.status,
                "tags": note.tags,
                "created_at": note.created_at
            }
            for note in notes[:limit]
        ]
        
        return {
            "total": len(tasks),
            "tasks": tasks,
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/tasks/{task_id}/update")
async def update_task(task_id: str, request: TaskUpdate):
    """更新任务"""
    try:
        asst = get_assistant()
        success = asst.update_task_status(
            task_id=task_id,
            new_status=request.status,
            comment=request.comment
        )
        
        return {
            "task_id": task_id,
            "success": success,
            "new_status": request.status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 文档处理 API ====================

@app.post("/api/documents/load")
async def load_document(request: DocumentLoadRequest):
    """加载文档"""
    try:
        asst = get_assistant()
        success = asst.load_document(request.file_path)
        
        return {
            "file_path": request.file_path,
            "success": success,
            "message": "文档加载成功" if success else "文档加载失败"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents/stats")
async def document_stats():
    """获取文档统计"""
    try:
        asst = get_assistant()
        stats = asst.get_stats()
        
        return {
            "documents_loaded": stats["documents_loaded"],
            "chunks_created": stats["chunks_created"],
            "questions_asked": stats["questions_asked"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== MCP 服务 API ====================

@app.post("/api/mcp/connect")
async def mcp_connect(request: MCPConnectRequest):
    """连接到 MCP 服务器"""
    try:
        asst = get_assistant()
        success = asst.connect_to_mcp_server(
            server_name=request.server_name,
            command=request.command,
            args=request.args
        )
        
        return {
            "server_name": request.server_name,
            "success": success,
            "message": "连接成功" if success else "连接失败"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mcp/call_tool")
async def mcp_call_tool(request: MCPToolCallRequest):
    """调用 MCP 工具"""
    try:
        asst = get_assistant()
        result = await asst.call_mcp_tool(
            server_name=request.server_name,
            tool_name=request.tool_name,
            arguments=request.arguments
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mcp/status")
async def mcp_status():
    """获取 MCP 状态"""
    try:
        asst = get_assistant()
        status = asst.get_mcp_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/mcp/disconnect")
async def mcp_disconnect(server_name: Optional[str] = None):
    """断开 MCP 连接"""
    try:
        asst = get_assistant()
        asst.disconnect_mcp_server(server_name)
        
        return {
            "server_name": server_name,
            "success": True,
            "message": "已断开连接"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== 统计和监控 API ====================

@app.get("/api/stats")
async def get_statistics():
    """获取完整统计信息"""
    try:
        if USE_DATABASE_ENHANCED:
            # 使用数据库增强版
            asst = get_assistant_db()
            stats = asst.get_stats()
        else:
            # 使用原有 FAISS 版本
            asst = get_assistant()
            stats = asst.get_stats()
        
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/report")
async def generate_report():
    """生成学习报告"""
    try:
        asst = get_assistant()
        report = asst.generate_learning_report("web_report.json")
        
        # 导出笔记
        asst.note_tool.export_notes("web_report_notes.json")
        
        return {
            "report_path": "web_report.json",
            "notes_path": "web_report_notes.json",
            "statistics": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== WebSocket 实时通信 ====================

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket 连接 - 用于实时通知"""
    await manager.connect(websocket)
    
    try:
        # 发送欢迎消息
        await manager.send_personal(
            websocket,
            {
                "type": "welcome",
                "message": f"欢迎，{client_id}",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # 保持连接并处理消息
        while True:
            data = await websocket.receive_text()
            
            # 处理客户端消息
            try:
                message = json.loads(data)
                
                # 广播消息（示例）
                if message.get("broadcast"):
                    await manager.broadcast({
                        "type": "broadcast",
                        "from": client_id,
                        "message": message.get("content"),
                        "timestamp": datetime.now().isoformat()
                    })
                
            except json.JSONDecodeError:
                await manager.send_personal(
                    websocket,
                    {"type": "error", "message": "无效的 JSON 格式"}
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast({
            "type": "notification",
            "message": f"用户 {client_id} 已断开连接"
        })

# ==================== 静态文件挂载 ====================

# 挂载静态文件目录（使用绝对路径）
static_path = BASE_DIR / "static"
print(f"📁 静态文件路径：{static_path}")
print(f"📁 静态文件是否存在：{static_path.exists()}")
if static_path.exists():
    app.mount("/static", StaticFiles(directory=static_path), name="static")
    print("✅ 静态文件已挂载到 /static")
else:
    print(f"❌ 静态文件路径不存在：{static_path}")

# ==================== 主程序入口 ====================

if __name__ == "__main__":
    print("=" * 80)
    print("🚀 启动 CodeMind Assistant Web API")
    print("=" * 80)
    print("\n访问地址:")
    print("  📱 前端界面：http://localhost:8000")
    print("  📚 API 文档：http://localhost:8000/docs")
    print("  🔍 ReDoc:   http://localhost:8000/redoc")
    print("\n功能列表:")
    print("  💬 智能问答      - /api/chat")
    print("  🗂️ 工作空间管理  - /api/workspace")
    print("  📤 文件上传      - /api/upload")
    print("  💾 会话管理      - /api/session")
    print("  🗂️ 代码库操作    - /api/codebase")
    print("  ✅ 任务管理      - /api/tasks")
    print("  📄 文档处理      - /api/documents")
    print("  🔌 MCP 服务控制  - /api/mcp")
    print("  📊 统计监控      - /api/stats")
    print("=" * 80)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
