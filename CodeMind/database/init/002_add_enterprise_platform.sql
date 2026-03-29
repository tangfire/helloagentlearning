-- 企业诊断平台 - 数据库迁移脚本
-- 执行时间：2026-03-29
-- 说明：新增企业管理、知识库、报告模板和诊断报告功能

-- ==================== 企业诊断平台新增表 ====================

-- ========== 企业信息表 ==========
CREATE TABLE enterprises (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) UNIQUE NOT NULL,  -- 企业唯一编码
    industry VARCHAR(100),  -- 行业
    scale VARCHAR(50),  -- 规模
    description TEXT,
    owner_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- 创建索引
CREATE INDEX idx_enterprises_owner ON enterprises(owner_id);
CREATE INDEX idx_enterprises_name ON enterprises(name);
CREATE INDEX idx_enterprises_code ON enterprises(code);

-- ========== 企业知识库表 ==========
CREATE TABLE enterprise_knowledge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enterprise_id UUID NOT NULL REFERENCES enterprises(id) ON DELETE CASCADE,
    title VARCHAR(300) NOT NULL,
    content TEXT,
    file_path VARCHAR(500),
    category VARCHAR(50),  -- 分类：财务、人力、运营、技术等
    doc_type VARCHAR(50),  -- 文档类型：制度、报告、数据等
    tags TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    version INTEGER DEFAULT 1,
    is_public BOOLEAN DEFAULT FALSE,  -- 是否公开共享
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_knowledge_enterprise ON enterprise_knowledge(enterprise_id);
CREATE INDEX idx_knowledge_category ON enterprise_knowledge(category);
CREATE INDEX idx_knowledge_tags ON enterprise_knowledge USING GIN(tags);
CREATE INDEX idx_knowledge_metadata ON enterprise_knowledge USING GIN(metadata);

-- ========== 诊断报告模板表 ==========
CREATE TABLE report_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(50),  -- 模板分类
    template_type VARCHAR(50),  -- 模板类型：综合、专项等
    structure JSONB DEFAULT '[]'::jsonb,  -- 报告结构定义
    prompt_template TEXT,  -- LLM 提示词模板
    ppt_template VARCHAR(500),  -- PPT 模板文件路径
    is_default BOOLEAN DEFAULT FALSE,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_template_category ON report_templates(category);
CREATE INDEX idx_template_type ON report_templates(template_type);
CREATE INDEX idx_template_created_by ON report_templates(created_by);

-- ========== 诊断分析报告表 ==========
CREATE TABLE diagnostic_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enterprise_id UUID NOT NULL REFERENCES enterprises(id) ON DELETE CASCADE,
    template_id UUID REFERENCES report_templates(id) ON DELETE SET NULL,
    title VARCHAR(300) NOT NULL,
    report_type VARCHAR(50) DEFAULT 'comprehensive',  -- 报告类型
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'generating', 'completed', 'failed')),
    analysis_query TEXT,  -- 分析查询条件/需求
    llm_analysis TEXT,  -- LLM 生成的分析内容
    conclusions JSONB DEFAULT '[]'::jsonb,  -- 结论列表
    recommendations JSONB DEFAULT '[]'::jsonb,  -- 建议列表
    ppt_file_path VARCHAR(500),  -- 生成的 PPT 文件路径
    pdf_file_path VARCHAR(500),  -- 生成的 PDF 文件路径
    metadata JSONB DEFAULT '{}'::jsonb,
    generated_by UUID REFERENCES users(id) ON DELETE SET NULL,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 创建索引
CREATE INDEX idx_report_enterprise ON diagnostic_reports(enterprise_id);
CREATE INDEX idx_report_template ON diagnostic_reports(template_id);
CREATE INDEX idx_report_status ON diagnostic_reports(status);
CREATE INDEX idx_report_generated_by ON diagnostic_reports(generated_by);
CREATE INDEX idx_report_created_at ON diagnostic_reports(created_at);

-- ========== 触发器（自动更新 updated_at） ==========
CREATE TRIGGER update_enterprises_updated_at BEFORE UPDATE ON enterprises
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_enterprise_knowledge_updated_at BEFORE UPDATE ON enterprise_knowledge
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_report_templates_updated_at BEFORE UPDATE ON report_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_diagnostic_reports_updated_at BEFORE UPDATE ON diagnostic_reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========== 插入默认数据 ==========

-- 默认报告模板：企业综合诊断报告
INSERT INTO report_templates (name, description, category, template_type, structure, prompt_template, is_default) VALUES
('企业综合诊断报告', '全面分析企业经营状况的综合诊断报告模板', '综合诊断', 'comprehensive', 
 '[
    {
      "section": "企业概况",
      "order": 1,
      "subsections": ["基本信息", "发展历程", "组织架构"]
    },
    {
      "section": "经营分析",
      "order": 2,
      "subsections": ["营收状况", "成本结构", "利润分析"]
    },
    {
      "section": "问题诊断",
      "order": 3,
      "subsections": ["主要问题", "原因分析", "影响评估"]
    },
    {
      "section": "改进建议",
      "order": 4,
      "subsections": ["短期措施", "中期规划", "长期战略"]
    }
  ]'::jsonb,
 '你是一位资深企业管理咨询顾问。请根据提供的企业资料，按照以下结构生成专业的诊断分析报告：

1. 企业概况：总结企业的基本信息、发展历程和组织架构
2. 经营分析：深入分析企业的营收、成本和利润状况
3. 问题诊断：识别企业面临的主要问题，分析根本原因和影响
4. 改进建议：提出具体可行的改进措施，包括短期、中期和长期规划

要求：
- 使用专业的商业术语
- 数据驱动的分析
- 逻辑清晰、层次分明
- 建议要具体可执行',
 TRUE);

-- 默认报告模板：财务健康诊断
INSERT INTO report_templates (name, description, category, template_type, structure, prompt_template, is_default) VALUES
('财务健康诊断报告', '专注于企业财务状况的诊断报告模板', '财务诊断', 'financial',
 '[
    {
      "section": "财务概况",
      "order": 1,
      "subsections": ["资产状况", "负债结构", "所有者权益"]
    },
    {
      "section": "盈利能力分析",
      "order": 2,
      "subsections": ["收入分析", "成本费用", "利润指标"]
    },
    {
      "section": "营运能力分析",
      "order": 3,
      "subsections": ["应收账款周转", "存货周转", "总资产周转"]
    },
    {
      "section": "偿债能力分析",
      "order": 4,
      "subsections": ["短期偿债能力", "长期偿债能力"]
    },
    {
      "section": "发展能力分析",
      "order": 5,
      "subsections": ["增长性指标", "可持续性评估"]
    }
  ]'::jsonb,
 '你是一位资深财务分析师。请根据企业财务数据，从以下维度进行全面分析：

1. 财务概况：资产负债结构、所有者权益变化
2. 盈利能力：毛利率、净利率、ROE 等关键指标
3. 营运能力：各类周转率分析
4. 偿债能力：流动比率、速动比率、资产负债率
5. 发展能力：收入增长率、利润增长率

要求：
- 使用专业财务分析框架
- 对比行业基准
- 识别财务风险点
- 提出改善建议',
 FALSE);

-- 默认报告模板：组织效能诊断
INSERT INTO report_templates (name, description, category, template_type, structure, prompt_template, is_default) VALUES
('组织效能诊断报告', '评估企业组织效能和人力资源管理水平的诊断模板', '组织诊断', 'organizational',
 '[
    {
      "section": "组织架构分析",
      "order": 1,
      "subsections": ["架构设计", "部门设置", "汇报关系"]
    },
    {
      "section": "人员配置分析",
      "order": 2,
      "subsections": ["人员结构", "人岗匹配", "编制情况"]
    },
    {
      "section": "流程效率分析",
      "order": 3,
      "subsections": ["决策流程", "协作效率", "响应速度"]
    },
    {
      "section": "激励机制分析",
      "order": 4,
      "subsections": ["薪酬体系", "绩效考核", "晋升通道"]
    },
    {
      "section": "改进建议",
      "order": 5,
      "subsections": ["架构优化", "流程再造", "机制创新"]
    }
  ]'::jsonb,
 '你是一位组织发展专家。请从以下维度评估企业的组织效能：

1. 组织架构：合理性、清晰度、适应性
2. 人员配置：结构优化、能力匹配、冗余度
3. 流程效率：决策链、协作机制、执行力
4. 激励机制：公平性、竞争性、有效性

要求：
- 运用组织管理理论
- 对标行业最佳实践
- 识别组织痛点
- 提供系统性改进方案',
 FALSE);

-- ========== 表注释 ==========
COMMENT ON TABLE enterprises IS '企业信息表 - 存储企业客户基本信息';
COMMENT ON TABLE enterprise_knowledge IS '企业知识库表 - 存储企业专属资料和文档';
COMMENT ON TABLE report_templates IS '诊断报告模板表 - 预置的报告生成模板';
COMMENT ON TABLE diagnostic_reports IS '诊断分析报告表 - 生成的企业诊断报告';

COMMENT ON COLUMN enterprises.code IS '企业唯一编码 - 用于标识和检索';
COMMENT ON COLUMN enterprises.industry IS '所属行业 - 用于行业对标分析';
COMMENT ON COLUMN enterprises.scale IS '企业规模 - 大型/中型/小型';

COMMENT ON COLUMN enterprise_knowledge.category IS '知识分类 - 财务/人力/运营/技术等';
COMMENT ON COLUMN enterprise_knowledge.doc_type IS '文档类型 - 制度/报告/数据等';

COMMENT ON COLUMN report_templates.structure IS '报告结构定义 - JSON 格式的章节结构';
COMMENT ON COLUMN report_templates.prompt_template IS 'LLM 提示词模板 - 指导 AI 生成报告';

COMMENT ON COLUMN diagnostic_reports.status IS '报告状态 - draft/generating/completed/failed';
COMMENT ON COLUMN diagnostic_reports.llm_analysis IS 'LLM 分析内容 - AI 生成的完整分析报告';
COMMENT ON COLUMN diagnostic_reports.conclusions IS '结论列表 - 关键发现总结';
COMMENT ON COLUMN diagnostic_reports.recommendations IS '建议列表 - 具体改进建议';
