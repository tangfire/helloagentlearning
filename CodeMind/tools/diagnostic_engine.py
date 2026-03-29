"""
企业诊断分析引擎

基于 RAG 知识库和 LLM 生成企业诊断分析报告
"""

import os
import dotenv
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from database.db_connection import get_db_context
from database.dao import (
    EnterpriseDAO, EnterpriseKnowledgeDAO, 
    DiagnosticReportDAO, ReportTemplateDAO
)

dotenv.load_dotenv()


class DiagnosticEngine:
    """
    企业诊断分析引擎
    
    核心功能：
    1. 从企业知识库检索相关信息
    2. 使用 LLM 进行智能分析
    3. 生成结构化的诊断报告
    """
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL", "gpt-4o-mini"),
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("BASE_URL"),
        )
        
    def analyze_enterprise(self, enterprise_id: str, 
                          analysis_query: str = None,
                          template_id: str = None) -> Dict[str, Any]:
        """
        分析企业并生成诊断报告
        
        Args:
            enterprise_id: 企业 ID（或工作空间 ID）
            analysis_query: 分析查询/需求
            template_id: 报告模板 ID
            
        Returns:
            诊断报告数据
        """
        with get_db_context() as db:
            enterprise_dao = EnterpriseDAO(db)
            knowledge_dao = EnterpriseKnowledgeDAO(db)
            report_dao = DiagnosticReportDAO(db)
            template_dao = ReportTemplateDAO(db)
            
            # 获取企业信息
            enterprise = enterprise_dao.get_enterprise(enterprise_id)
            
            # 如果没有找到企业记录，尝试从 Workspace 创建虚拟企业对象
            if not enterprise:
                from database.dao import WorkspaceDAO
                workspace_dao = WorkspaceDAO(db)
                workspace = workspace_dao.get_workspace(enterprise_id)
                
                if workspace:
                    print(f"   ℹ️ 未找到企业记录，使用工作空间：{workspace.name}")
                    # 创建一个简单的命名空间对象
                    class VirtualEnterprise:
                        def __init__(self, ws):
                            self.id = ws.id
                            self.name = ws.name
                            self.code = f"WS_{str(ws.id)[:8]}"
                            self.industry = "未知"
                            self.scale = "未知"
                            self.description = ws.description or "工作空间企业"
                    
                    enterprise = VirtualEnterprise(workspace)
                else:
                    raise ValueError(f"企业/工作空间不存在：{enterprise_id}")
            
            print(f"🔍 开始分析：{enterprise.name}")
            
            # 获取企业知识库内容
            knowledge_items = knowledge_dao.get_enterprise_knowledge(enterprise_id)
            knowledge_context = self._build_knowledge_context(knowledge_items)
            
            # 获取报告模板
            template = None
            if template_id:
                template = template_dao.get_template(template_id)
            
            # 如果没有指定模板，使用默认的综合诊断模板
            if not template:
                default_templates = template_dao.get_default_templates()
                template = default_templates[0] if default_templates else None
            
            # 构建分析提示词
            prompt = self._build_analysis_prompt(
                enterprise=enterprise,
                knowledge_context=knowledge_context,
                analysis_query=analysis_query,
                template=template
            )
            
            # 调用 LLM 进行分析
            print("🤖 AI 正在分析...")
            response = self.llm.invoke(prompt)
            analysis_result = response.content
            
            # 解析分析结果
            report_data = self._parse_analysis_result(analysis_result, template)
            
            return {
                'enterprise': enterprise,
                'template': template,
                'analysis': analysis_result,
                'conclusions': report_data.get('conclusions', []),
                'recommendations': report_data.get('recommendations', [])
            }
    
    def _build_knowledge_context(self, knowledge_items: List) -> str:
        """构建知识库上下文"""
        if not knowledge_items:
            return "暂无企业资料"
        
        context_parts = []
        for item in knowledge_items:
            part = f"""
【{item.category} - {item.doc_type}】
标题：{item.title}
内容：{item.content[:500] if item.content else '无'}
"""
            context_parts.append(part)
        
        return "\n".join(context_parts)
    
    def _build_analysis_prompt(self, enterprise, knowledge_context: str,
                              analysis_query: str = None,
                              template=None) -> ChatPromptTemplate:
        """构建分析提示词"""
        
        # 基础信息
        base_info = f"""
企业名称：{enterprise.name}
企业编码：{enterprise.code}
所属行业：{enterprise.industry or '未指定'}
企业规模：{enterprise.scale or '未指定'}
企业描述：{enterprise.description or '无'}
"""
        
        # 使用模板的提示词
        if template and template.prompt_template:
            system_prompt = template.prompt_template
        else:
            system_prompt = """你是一位资深企业管理咨询顾问。请根据提供的企业资料进行专业分析。

请按照以下结构生成诊断报告：
1. 企业概况总结
2. 经营现状分析
3. 主要问题诊断
4. 改进建议方案

要求：
- 分析要深入、具体
- 使用专业的商业术语
- 提出可执行的建议"""
        
        # 构建完整的提示词
        user_prompt = f"""
请分析以下企业资料：

【企业基本信息】
{base_info}

【企业知识库资料】
{knowledge_context}

【分析要求】
{analysis_query or '进行全面的企业诊断分析'}

请生成详细的诊断分析报告。
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])
        
        return prompt
    
    def _parse_analysis_result(self, analysis_text: str, template=None) -> Dict[str, Any]:
        """
        解析 LLM 生成的分析结果
        
        提取结论和建议
        """
        # 简单的文本解析，实际可以使用更复杂的 NLP 技术
        conclusions = []
        recommendations = []
        
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测章节标题
            if any(keyword in line.lower() for keyword in ['结论', '总结', '发现']):
                current_section = 'conclusion'
            elif any(keyword in line.lower() for keyword in ['建议', '方案', '措施']):
                current_section = 'recommendation'
            
            # 提取要点
            if line.startswith('- ') or line.startswith('• ') or line[0].isdigit():
                content = line.lstrip('- •').strip()
                if any(char.isdigit() for char in line[:2]):
                    content = line.split('. ', 1)[-1] if '. ' in line else line
                
                if current_section == 'conclusion':
                    conclusions.append(content)
                elif current_section == 'recommendation':
                    recommendations.append(content)
        
        # 如果没有解析出内容，使用整个分析文本
        if not conclusions and not recommendations:
            conclusions = [analysis_text[:500]]
        
        return {
            'conclusions': conclusions,
            'recommendations': recommendations
        }
    
    def generate_report(self, enterprise_id: str,
                       title: str,
                       analysis_query: str = None,
                       template_id: str = None,
                       generated_by: str = None) -> str:
        """
        生成完整的诊断报告（包括保存到数据库）
        
        Args:
            enterprise_id: 企业 ID
            title: 报告标题
            analysis_query: 分析查询
            template_id: 模板 ID
            generated_by: 生成者用户 ID
            
        Returns:
            报告 ID
        """
        with get_db_context() as db:
            report_dao = DiagnosticReportDAO(db)
            
            # 创建报告记录
            report = report_dao.create_report(
                enterprise_id=enterprise_id,
                title=title,
                template_id=template_id,
                analysis_query=analysis_query,
                generated_by=generated_by
            )
            
            try:
                # 更新状态为生成中
                report_dao.update_report_status(report.id, 'generating')
                
                # 执行分析
                result = self.analyze_enterprise(
                    enterprise_id=enterprise_id,
                    analysis_query=analysis_query,
                    template_id=template_id
                )
                
                # 更新报告内容
                report_dao.update_report_content(
                    report_id=report.id,
                    llm_analysis=result['analysis'],
                    conclusions=result['conclusions'],
                    recommendations=result['recommendations']
                )
                
                # 更新状态为完成
                report_dao.update_report_status(report.id, 'completed')
                
                print(f"✅ 报告生成成功：{title}")
                return str(report.id)
                
            except Exception as e:
                # 更新状态为失败
                report_dao.update_report_status(report.id, 'failed', str(e))
                print(f"❌ 报告生成失败：{e}")
                raise
