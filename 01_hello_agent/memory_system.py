"""
多层次记忆系统模块
实现工作记忆、情景记忆、语义记忆和感知记忆的管理
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum


class MemoryType(Enum):
    """记忆类型枚举"""
    WORKING = "working"  # 工作记忆
    EPISODIC = "episodic"  # 情景记忆
    SEMANTIC = "semantic"  # 语义记忆
    PERCEPTUAL = "perceptual"  # 感知记忆


@dataclass
class Memory:
    """记忆基类"""
    id: str = field(default_factory=lambda: hashlib.md5(
        f"{datetime.now().isoformat()}_{id}".encode()
    ).hexdigest())
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            **asdict(self),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


@dataclass
class WorkingMemory(Memory):
    """
    工作记忆：管理当前学习任务和上下文
    - 保存当前的对话历史
    - 记录正在处理的任务
    - 维护短期上下文信息
    """
    task_id: str = ""
    context: List[str] = field(default_factory=list)
    current_focus: str = ""
    attention_level: float = 1.0  # 注意力水平 0-1
    expiry_time: Optional[datetime] = None
    
    def add_context(self, text: str, max_length: int = 10):
        """添加上下文，保持最大长度"""
        self.context.append(text)
        if len(self.context) > max_length:
            self.context.pop(0)
        self.updated_at = datetime.now()
    
    def clear(self):
        """清空工作记忆"""
        self.context = []
        self.current_focus = ""
        self.updated_at = datetime.now()


@dataclass
class EpisodicMemory(Memory):
    """
    情景记忆：记录学习事件和查询历史
    - 记录每次问答交互
    - 保存学习路径
    - 追踪时间戳和结果
    """
    event_type: str = ""  # query, answer, learning_session
    query: str = ""
    response: str = ""
    sources: List[str] = field(default_factory=list)
    success: bool = True
    feedback_score: Optional[float] = None  # 用户反馈评分
    tags: List[str] = field(default_factory=list)
    related_memories: List[str] = field(default_factory=list)
    
    def add_tag(self, tag: str):
        """添加标签"""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()


@dataclass
class SemanticMemory(Memory):
    """
    语义记忆：存储概念知识和理解
    - 抽象的概念和定义
    - 知识点之间的关系
    - 从文档中提取的核心知识
    """
    concept: str = ""
    definition: str = ""
    category: str = ""
    related_concepts: List[str] = field(default_factory=list)
    confidence: float = 1.0  # 置信度 0-1
    source_documents: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    
    def add_relation(self, concept: str):
        """添加关联概念"""
        if concept not in self.related_concepts:
            self.related_concepts.append(concept)
            self.updated_at = datetime.now()


@dataclass
class PerceptualMemory(Memory):
    """
    感知记忆：处理文档特征和多模态信息
    - 文档的视觉特征
    - 图表、公式的位置
    - 多模态 embeddings
    """
    document_id: str = ""
    feature_type: str = ""  # image, table, formula, layout
    embedding: List[float] = field(default_factory=list)
    location: Dict[str, Any] = field(default_factory=dict)  # page, bbox
    description: str = ""
    raw_data: Optional[str] = None  # base64 encoded image etc.
    
    def set_location(self, page: int, bbox: Optional[List[float]] = None):
        """设置位置信息"""
        self.location = {"page": page}
        if bbox:
            self.location["bbox"] = bbox
        self.updated_at = datetime.now()


class MemoryManager:
    """
    记忆管理器：统一管理四种记忆类型
    """
    
    def __init__(self, user_id: str = "default_user"):
        self.user_id = user_id
        
        # 四种记忆存储
        self.working_memories: Dict[str, WorkingMemory] = {}
        self.episodic_memories: Dict[str, EpisodicMemory] = {}
        self.semantic_memories: Dict[str, SemanticMemory] = {}
        self.perceptual_memories: Dict[str, PerceptualMemory] = {}
        
        # 当前活跃的工作记忆
        self.current_working_memory: Optional[WorkingMemory] = None
        
        # 记忆索引（用于快速检索）
        self.episodic_index: Dict[str, List[str]] = {}  # tag -> memory_ids
        self.semantic_index: Dict[str, List[str]] = {}  # category -> memory_ids
    
    def create_working_memory(self, task_id: str, focus: str) -> WorkingMemory:
        """创建工作记忆"""
        wm = WorkingMemory(
            task_id=task_id,
            current_focus=focus
        )
        self.working_memories[wm.id] = wm
        self.current_working_memory = wm
        return wm
    
    def add_episodic_memory(self, 
                           event_type: str,
                           query: str,
                           response: str,
                           sources: List[str] = None,
                           tags: List[str] = None) -> EpisodicMemory:
        """添加情景记忆"""
        em = EpisodicMemory(
            event_type=event_type,
            query=query,
            response=response,
            sources=sources or [],
            tags=tags or []
        )
        self.episodic_memories[em.id] = em
        
        # 更新索引
        for tag in em.tags:
            if tag not in self.episodic_index:
                self.episodic_index[tag] = []
            self.episodic_index[tag].append(em.id)
        
        # 添加到当前工作记忆的关联中
        if self.current_working_memory:
            self.current_working_memory.add_context(f"{query}: {response}")
        
        return em
    
    def add_semantic_memory(self,
                           concept: str,
                           definition: str,
                           category: str,
                           related_concepts: List[str] = None,
                           source_documents: List[str] = None,
                           confidence: float = 1.0) -> SemanticMemory:
        """添加语义记忆"""
        sm = SemanticMemory(
            concept=concept,
            definition=definition,
            category=category,
            related_concepts=related_concepts or [],
            source_documents=source_documents or [],
            confidence=confidence
        )
        self.semantic_memories[sm.id] = sm
        
        # 更新索引
        if category not in self.semantic_index:
            self.semantic_index[category] = []
        self.semantic_index[category].append(sm.id)
        
        return sm
    
    def add_perceptual_memory(self,
                             document_id: str,
                             feature_type: str,
                             description: str,
                             embedding: List[float] = None,
                             page: int = None,
                             bbox: List[float] = None) -> PerceptualMemory:
        """添加感知记忆"""
        pm = PerceptualMemory(
            document_id=document_id,
            feature_type=feature_type,
            description=description,
            embedding=embedding or []
        )
        if page is not None:
            pm.set_location(page, bbox)
        
        self.perceptual_memories[pm.id] = pm
        return pm
    
    def search_episodic_memories(self, 
                                 tags: List[str] = None,
                                 query_keywords: str = None,
                                 limit: int = 10) -> List[EpisodicMemory]:
        """搜索情景记忆"""
        results = []
        
        # 按标签搜索
        if tags:
            memory_ids = set()
            for tag in tags:
                if tag in self.episodic_index:
                    memory_ids.update(self.episodic_index[tag])
            
            for mid in memory_ids:
                if mid in self.episodic_memories:
                    results.append(self.episodic_memories[mid])
        
        # 按查询关键词搜索
        elif query_keywords:
            for em in self.episodic_memories.values():
                if (query_keywords.lower() in em.query.lower() or
                    query_keywords.lower() in em.response.lower()):
                    results.append(em)
        else:
            results = list(self.episodic_memories.values())
        
        # 按时间排序，返回最新的
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]
    
    def search_semantic_memories(self,
                                category: str = None,
                                concept_keywords: str = None,
                                limit: int = 20) -> List[SemanticMemory]:
        """搜索语义记忆"""
        results = []
        
        # 按类别搜索
        if category and category in self.semantic_index:
            for mid in self.semantic_index[category]:
                if mid in self.semantic_memories:
                    results.append(self.semantic_memories[mid])
        
        # 按概念关键词搜索
        elif concept_keywords:
            for sm in self.semantic_memories.values():
                if (concept_keywords.lower() in sm.concept.lower() or
                    concept_keywords.lower() in sm.definition.lower()):
                    results.append(sm)
        else:
            results = list(self.semantic_memories.values())
        
        # 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)
        return results[:limit]
    
    def integrate_memories(self, 
                          episodic_ids: List[str],
                          semantic_concept: str,
                          semantic_definition: str,
                          category: str) -> SemanticMemory:
        """
        整合记忆：从多个情景记忆中提取知识，形成语义记忆
        """
        # 收集相关的情景记忆
        related_queries = []
        related_responses = []
        all_sources = []
        
        for eid in episodic_ids:
            if eid in self.episodic_memories:
                em = self.episodic_memories[eid]
                related_queries.append(em.query)
                related_responses.append(em.response)
                all_sources.extend(em.sources)
        
        # 创建语义记忆
        sm = self.add_semantic_memory(
            concept=semantic_concept,
            definition=semantic_definition,
            category=category,
            source_documents=list(set(all_sources)),
            confidence=0.9  # 整合后的记忆置信度稍低
        )
        
        # 建立关联
        sm.related_concepts = episodic_ids
        return sm
    
    def forget_old_memories(self, 
                           days_threshold: int = 30,
                           min_feedback_score: float = 0.5) -> Dict[str, int]:
        """
        遗忘机制：清理旧的低质量记忆
        """
        cutoff_date = datetime.now()
        from datetime import timedelta
        cutoff_date = cutoff_date - timedelta(days=days_threshold)
        
        forgotten = {
            "episodic": 0,
            "semantic": 0,
            "perceptual": 0
        }
        
        # 遗忘旧的情景记忆
        to_forget = []
        for eid, em in self.episodic_memories.items():
            if (em.created_at < cutoff_date and 
                (em.feedback_score is None or em.feedback_score < min_feedback_score)):
                to_forget.append(eid)
        
        for eid in to_forget:
            del self.episodic_memories[eid]
            forgotten["episodic"] += 1
        
        # 可以从索引中也移除
        for tag, mids in self.episodic_index.items():
            self.episodic_index[tag] = [mid for mid in mids if mid in self.episodic_memories]
        
        return forgotten
    
    def get_learning_report(self) -> Dict[str, Any]:
        """生成学习报告"""
        now = datetime.now()
        
        # 统计信息
        total_episodic = len(self.episodic_memories)
        total_semantic = len(self.semantic_memories)
        total_perceptual = len(self.perceptual_memories)
        
        # 最近的学习活动
        recent_episodes = self.search_episodic_memories(limit=10)
        
        # 知识点掌握情况
        categories = {}
        for sm in self.semantic_memories.values():
            if sm.category not in categories:
                categories[sm.category] = 0
            categories[sm.category] += 1
        
        # 成功率统计
        successful_queries = sum(1 for em in self.episodic_memories.values() if em.success)
        success_rate = successful_queries / total_episodic if total_episodic > 0 else 0
        
        return {
            "report_time": now.isoformat(),
            "user_id": self.user_id,
            "statistics": {
                "total_episodic_memories": total_episodic,
                "total_semantic_memories": total_semantic,
                "total_perceptual_memories": total_perceptual,
                "success_rate": success_rate
            },
            "knowledge_categories": categories,
            "recent_activities": [em.to_dict() for em in recent_episodes],
            "top_concepts": [
                {"concept": sm.concept, "confidence": sm.confidence}
                for sm in sorted(
                    self.semantic_memories.values(),
                    key=lambda x: x.confidence,
                    reverse=True
                )[:10]
            ]
        }
    
    def export_memories(self, filepath: str):
        """导出记忆到 JSON 文件"""
        data = {
            "user_id": self.user_id,
            "export_time": datetime.now().isoformat(),
            "working_memories": [wm.to_dict() for wm in self.working_memories.values()],
            "episodic_memories": [em.to_dict() for em in self.episodic_memories.values()],
            "semantic_memories": [sm.to_dict() for sm in self.semantic_memories.values()],
            "perceptual_memories": [pm.to_dict() for pm in self.perceptual_memories.values()]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def import_memories(self, filepath: str):
        """从 JSON 文件导入记忆"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 简单的导入逻辑，可以根据需要完善
        print(f"从 {filepath} 导入记忆数据...")
        print(f"用户 ID: {data.get('user_id')}")
        print(f"导出时间：{data.get('export_time')}")
