"""
NoteTool - 笔记工具

用于记录长期任务中的发现、问题和决策。
支持结构化笔记、标签分类和跨会话检索。
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field, asdict


@dataclass
class Note:
    """笔记数据结构"""
    id: str
    title: str
    content: str
    note_type: str  # observation, issue, decision, task, summary
    tags: List[str] = field(default_factory=list)
    related_files: List[str] = field(default_factory=list)
    priority: str = "medium"  # low, medium, high, critical
    status: str = "open"  # open, in_progress, resolved, closed
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


class NoteTool:
    """
    笔记工具
    
    核心功能：
    1. 记录代码库探索发现
    2. 追踪问题和改进点
    3. 管理长期重构任务
    4. 支持标签检索和状态管理
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化笔记工具
        
        Args:
            storage_path: 笔记存储路径（可选，默认内存存储）
        """
        self.notes: Dict[str, Note] = {}
        self.storage_path = Path(storage_path) if storage_path else None
        
        # 加载已有笔记
        if self.storage_path and self.storage_path.exists():
            self._load_notes()
        
        # 统计信息
        self.stats = {
            "total_notes": 0,
            "by_type": {},
            "by_status": {},
            "by_priority": {}
        }
    
    def create_note(self, 
                   title: str,
                   content: str,
                   note_type: str,
                   tags: Optional[List[str]] = None,
                   related_files: Optional[List[str]] = None,
                   priority: str = "medium",
                   status: str = "open") -> Note:
        """
        创建新笔记
        
        Args:
            title: 标题
            content: 内容
            note_type: 类型 (observation/issue/decision/task/summary)
            tags: 标签列表
            related_files: 相关文件路径
            priority: 优先级
            status: 状态
            
        Returns:
            创建的笔记对象
        """
        note_id = f"note_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.notes)}"
        
        note = Note(
            id=note_id,
            title=title,
            content=content,
            note_type=note_type,
            tags=tags or [],
            related_files=related_files or [],
            priority=priority,
            status=status
        )
        
        self.notes[note_id] = note
        self._update_stats()
        
        print(f"📝 创建笔记：{title[:50]}...")
        return note
    
    def get_note(self, note_id: str) -> Optional[Note]:
        """获取笔记"""
        return self.notes.get(note_id)
    
    def update_note(self, note_id: str, **updates) -> bool:
        """
        更新笔记
        
        Args:
            note_id: 笔记 ID
            **updates: 要更新的字段
            
        Returns:
            是否成功更新
        """
        if note_id not in self.notes:
            return False
        
        note = self.notes[note_id]
        
        for key, value in updates.items():
            if hasattr(note, key):
                setattr(note, key, value)
        
        note.updated_at = datetime.now().isoformat()
        self._update_stats()
        
        return True
    
    def search_notes(self, 
                    query: Optional[str] = None,
                    note_type: Optional[str] = None,
                    tags: Optional[List[str]] = None,
                    status: Optional[str] = None,
                    limit: int = 20) -> List[Note]:
        """
        搜索笔记
        
        Args:
            query: 关键词查询
            note_type: 按类型筛选
            tags: 按标签筛选
            status: 按状态筛选
            limit: 返回数量限制
            
        Returns:
            匹配的笔记列表
        """
        results = list(self.notes.values())
        
        # 类型筛选
        if note_type:
            results = [n for n in results if n.note_type == note_type]
        
        # 状态筛选
        if status:
            results = [n for n in results if n.status == status]
        
        # 标签筛选
        if tags:
            results = [n for n in results if any(tag in n.tags for tag in tags)]
        
        # 关键词查询
        if query:
            query_lower = query.lower()
            filtered = []
            for note in results:
                if (query_lower in note.title.lower() or 
                    query_lower in note.content.lower() or
                    any(query_lower in tag.lower() for tag in note.tags)):
                    filtered.append(note)
            results = filtered
        
        # 按优先级和时间排序
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        results.sort(key=lambda x: (priority_order.get(x.priority, 2), x.created_at), reverse=True)
        
        return results[:limit]
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取笔记摘要
        
        Returns:
            包含统计信息的摘要字典
        """
        open_issues = len([n for n in self.notes.values() 
                          if n.note_type == "issue" and n.status == "open"])
        
        pending_tasks = len([n for n in self.notes.values() 
                            if n.note_type == "task" and n.status in ["open", "in_progress"]])
        
        return {
            "total_notes": len(self.notes),
            "open_issues": open_issues,
            "pending_tasks": pending_tasks,
            "statistics": self.stats,
            "recent_notes": [
                {
                    "id": n.id,
                    "title": n.title,
                    "type": n.note_type,
                    "status": n.status,
                    "created_at": n.created_at
                }
                for n in sorted(self.notes.values(), 
                              key=lambda x: x.created_at, 
                              reverse=True)[:5]
            ]
        }
    
    def export_notes(self, filepath: str, format: str = "json") -> bool:
        """导出笔记"""
        try:
            path = Path(filepath)
            
            if format == "json":
                data = {
                    "exported_at": datetime.now().isoformat(),
                    "total_notes": len(self.notes),
                    "notes": [asdict(note) for note in self.notes.values()]
                }
                
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 已导出 {len(self.notes)} 条笔记到 {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ 导出失败：{e}")
            return False
    
    def _load_notes(self):
        """从文件加载笔记"""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for note_data in data.get("notes", []):
                    note = Note(**note_data)
                    self.notes[note.id] = note
            
            self._update_stats()
            print(f"📂 已加载 {len(self.notes)} 条笔记")
            
        except Exception as e:
            print(f"⚠️ 加载笔记失败：{e}")
    
    def _update_stats(self):
        """更新统计信息"""
        self.stats["total_notes"] = len(self.notes)
        
        # 按类型统计
        by_type = {}
        for note in self.notes.values():
            by_type[note.note_type] = by_type.get(note.note_type, 0) + 1
        self.stats["by_type"] = by_type
        
        # 按状态统计
        by_status = {}
        for note in self.notes.values():
            by_status[note.status] = by_status.get(note.status, 0) + 1
        self.stats["by_status"] = by_status
        
        # 按优先级统计
        by_priority = {}
        for note in self.notes.values():
            by_priority[note.priority] = by_priority.get(note.priority, 0) + 1
        self.stats["by_priority"] = by_priority
    
    def save(self):
        """保存到文件"""
        if self.storage_path:
            self.export_notes(str(self.storage_path))
