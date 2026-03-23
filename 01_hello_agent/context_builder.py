"""
ContextBuilder - 上下文构建器

负责智能筛选和组织上下文信息，确保高信号密度。
在长程任务中管理跨会话的上下文质量与相关性。
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional


class ContextBuilder:
    """
    上下文构建器
    
    核心功能：
    1. 智能筛选历史信息，保留高相关性内容
    2. 组织多源上下文（笔记、终端输出、代码分析）
    3. 维护跨会话的连贯性
    4. 动态调整上下文窗口，优化 token 使用
    """
    
    def __init__(self, max_context_length: int = 8000):
        """
        初始化上下文构建器
        
        Args:
            max_context_length: 最大上下文长度（字符数）
        """
        self.max_context_length = max_context_length
        self.context_history: List[Dict[str, Any]] = []
        self.priority_topics: List[str] = []  # 高优先级话题
        self.ignored_topics: List[str] = []   # 低优先级话题
        
        # 上下文统计
        self.stats = {
            "total_entries": 0,
            "total_length": 0,
            "compressions_performed": 0
        }
    
    def add_entry(self, entry_type: str, content: str, metadata: Optional[Dict] = None):
        """
        添加上下文条目
        
        Args:
            entry_type: 条目类型 (note, terminal, code_analysis, task_update)
            content: 内容
            metadata: 元数据
        """
        entry = {
            "id": f"ctx_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.context_history)}",
            "type": entry_type,
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
            "relevance_score": 1.0,  # 初始相关性分数
            "access_count": 0  # 访问次数
        }
        
        self.context_history.append(entry)
        self.stats["total_entries"] += 1
        self.stats["total_length"] += len(content)
    
    def build_context(self, current_query: str, include_types: Optional[List[str]] = None) -> str:
        """
        构建针对当前查询的优化上下文
        
        Args:
            current_query: 当前查询/问题
            include_types: 包含的条目类型列表
            
        Returns:
            优化后的上下文字符串
        """
        # 1. 筛选相关条目
        relevant_entries = self._filter_relevant_entries(current_query, include_types)
        
        # 2. 按相关性排序
        sorted_entries = sorted(relevant_entries, key=lambda x: (x["relevance_score"], x["access_count"]), reverse=True)
        
        # 3. 动态截断以适应上下文窗口
        context_entries = self._adapt_to_window(sorted_entries)
        
        # 4. 格式化为可读上下文
        formatted_context = self._format_context(context_entries)
        
        # 5. 更新访问统计
        for entry in context_entries:
            entry["access_count"] += 1
        
        return formatted_context
    
    def _filter_relevant_entries(self, query: str, include_types: Optional[List[str]] = None) -> List[Dict]:
        """
        筛选相关条目
        
        策略：
        - 优先保留最近的高访问频次条目
        - 匹配关键词和话题
        - 排除低优先级话题
        """
        filtered = []
        
        for entry in self.context_history:
            # 类型过滤
            if include_types and entry["type"] not in include_types:
                continue
            
            # 排除低优先级话题
            if any(topic in entry["content"].lower() for topic in self.ignored_topics):
                continue
            
            # 计算相关性分数
            relevance = self._calculate_relevance(entry, query)
            entry["relevance_score"] = relevance
            
            # 只保留相关性高于阈值的条目
            if relevance >= 0.3:
                filtered.append(entry)
        
        return filtered
    
    def _calculate_relevance(self, entry: Dict, query: str) -> float:
        """
        计算条目与查询的相关性分数
        
        考虑因素：
        - 时间衰减（越新越相关）
        - 访问频次（高频访问更相关）
        - 关键词匹配
        - 话题优先级
        """
        base_score = 0.5
        
        # 1. 时间衰减（指数衰减，7 天半衰期）
        entry_time = datetime.fromisoformat(entry["timestamp"])
        time_diff = (datetime.now() - entry_time).total_seconds() / 86400  # 转换为天数
        time_decay = 0.5 ** (time_diff / 7)
        
        # 2. 访问频次加分
        access_bonus = min(0.3, entry["access_count"] * 0.05)
        
        # 3. 关键词匹配
        query_words = set(query.lower().split())
        content_words = set(entry["content"].lower().split())
        keyword_match = len(query_words & content_words) / max(len(query_words), 1)
        keyword_bonus = keyword_match * 0.4
        
        # 4. 话题优先级
        priority_bonus = 0.0
        if any(topic in entry["content"] for topic in self.priority_topics):
            priority_bonus = 0.2
        
        # 综合分数
        final_score = base_score * time_decay + access_bonus + keyword_bonus + priority_bonus
        
        return min(1.0, final_score)  # 限制在 0-1 范围内
    
    def _adapt_to_window(self, entries: List[Dict]) -> List[Dict]:
        """
        动态调整条目数量以适应上下文窗口
        
        策略：
        - 优先保留高相关性条目
        - 渐进式截断
        - 确保至少保留 3 个条目（如果可用）
        """
        if not entries:
            return []
        
        accumulated_length = 0
        selected_entries = []
        
        for entry in entries:
            entry_length = len(entry["content"]) + 100  # 加上格式化开销
            
            if accumulated_length + entry_length <= self.max_context_length:
                selected_entries.append(entry)
                accumulated_length += entry_length
            else:
                break
        
        # 确保至少有 3 个条目
        if len(selected_entries) < 3 and len(entries) >= 3:
            selected_entries = entries[:3]
        
        return selected_entries
    
    def _format_context(self, entries: List[Dict]) -> str:
        """
        格式化上下文为可读字符串
        
        Returns:
            格式化后的上下文字符串
        """
        if not entries:
            return ""
        
        sections = []
        
        # 按类型分组
        by_type = {}
        for entry in entries:
            entry_type = entry["type"]
            if entry_type not in by_type:
                by_type[entry_type] = []
            by_type[entry_type].append(entry)
        
        # 格式化每个类型的内容
        type_names = {
            "note": "📝 笔记",
            "terminal": "💻 终端输出",
            "code_analysis": "🔍 代码分析",
            "task_update": "✅ 任务更新"
        }
        
        for entry_type, type_entries in by_type.items():
            type_name = type_names.get(entry_type, entry_type.upper())
            section_lines = [f"\n{'='*60}", f"{type_name}", f'{"="*60}']
            
            for entry in type_entries:
                timestamp = entry["timestamp"][:16].replace('T', ' ')
                content_preview = entry["content"][:500]
                
                section_lines.append(f"\n[{timestamp}]")
                section_lines.append(content_preview)
                
                # 添加元数据
                if entry.get("metadata"):
                    meta_str = ", ".join(f"{k}={v}" for k, v in entry["metadata"].items())
                    section_lines.append(f"  元数据：{meta_str}")
            
            sections.append("\n".join(section_lines))
        
        # 添加摘要
        summary = [
            "\n" + "="*60,
            "📊 上下文摘要",
            "="*60,
            f"总条目数：{len(entries)}",
            f"总长度：{sum(len(e['content']) for e in entries)} 字符",
            f"上下文窗口使用率：{sum(len(e['content']) for e in entries) / self.max_context_length:.1%}"
        ]
        sections.append("\n".join(summary))
        
        return "\n".join(sections)
    
    def set_priority_topics(self, topics: List[str]):
        """设置高优先级话题"""
        self.priority_topics = topics
        print(f"🎯 设置优先话题：{topics}")
    
    def set_ignored_topics(self, topics: List[str]):
        """设置忽略的话题"""
        self.ignored_topics = topics
        print(f"🚫 设置忽略话题：{topics}")
    
    def clear_history(self):
        """清空历史"""
        self.context_history = []
        self.stats = {
            "total_entries": 0,
            "total_length": 0,
            "compressions_performed": 0
        }
        print("🗑️ 已清空上下文历史")
    
    def get_summary(self) -> Dict[str, Any]:
        """获取上下文摘要"""
        return {
            "total_entries": len(self.context_history),
            "total_length": self.stats["total_length"],
            "max_context_length": self.max_context_length,
            "priority_topics": self.priority_topics,
            "recent_entries": [
                {
                    "type": e["type"],
                    "timestamp": e["timestamp"],
                    "length": len(e["content"])
                }
                for e in sorted(self.context_history, 
                              key=lambda x: x["timestamp"], 
                              reverse=True)[:5]
            ]
        }
