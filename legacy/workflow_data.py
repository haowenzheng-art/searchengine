
"""
Workflow Thief Arena - 共享数据模块
三个版本共用同一套数据
"""
import json

# ==================== 预设工作流数据 ====================

RECRUITMENT_DATA = {
    "name": "企业招聘筛选流程",
    "short_name": "招聘筛选",
    "workflow_name": "企业招聘筛选流程",
    "industry": "人力资源服务业",
    "trigger_condition": "业务部门提出招聘需求，经审批后发布职位",
    "trigger": "业务部门提出招聘需求，经审批后发布职位",
    "roles": ["招聘专员", "招聘经理", "业务部门面试官", "HRBP", "候选人"],
    "systems": ["招聘管理系统", "ATS简历跟踪系统", "企业邮箱", "视频面试平台", "OA审批系统"],
    "metrics": {"steps": 8, "saving": "37.8万", "roi": "656%", "payback": "2个月"},
    "steps": [
        {"step_number": 1, "description": "需求收集与审批", "role": "业务部门经理", "input": "业务扩张计划/岗位空缺", "output": "经审批的招聘需求单", "system": "OA审批系统", "estimated_duration_minutes": 120, "is_decision": False},
        {"step_number": 2, "description": "职位发布与渠道管理", "role": "招聘专员", "input": "审批通过的招聘需求", "output": "多渠道发布的职位广告", "system": "招聘管理系统", "estimated_duration_minutes": 60, "is_decision": False},
        {"step_number": 3, "description": "简历收集与初筛", "role": "招聘专员", "input": "各渠道投递的简历", "output": "筛选后的简历长名单", "system": "ATS简历跟踪系统", "estimated_duration_minutes": 180, "is_decision": False},
        {"step_number": 4, "description": "简历复核与面试安排", "role": "招聘经理", "input": "初筛简历长名单", "output": "面试安排表", "system": "企业邮箱/日历系统", "estimated_duration_minutes": 90, "is_decision": False},
        {"step_number": 5, "description": "初轮面试", "role": "业务部门面试官", "input": "候选人简历", "output": "面试评估表", "system": "视频面试平台", "estimated_duration_minutes": 60, "is_decision": True},
        {"step_number": 6, "description": "复试与终面", "role": "业务部门负责人/HRBP", "input": "初面通过名单", "output": "终面评估报告", "system": "视频面试平台", "estimated_duration_minutes": 60, "is_decision": True},
        {"step_number": 7, "description": "背景调查与offer审批", "role": "招聘专员/HRBP", "input": "终面通过候选人", "output": "背调报告与offer审批单", "system": "OA审批系统", "estimated_duration_minutes": 240, "is_decision": False},
        {"step_number": 8, "description": "offer发放与入职准备", "role": "招聘专员", "input": "审批通过的offer", "output": "入职通知书与入职材料清单", "system": "企业邮箱", "estimated_duration_minutes": 60, "is_decision": False}
    ],
    "pain_points": {
        "manual_repetition": {"description": "简历初筛需要人工逐一查看每份简历，重复进行关键词匹配、经历核对等机械性工作", "step_numbers": [3], "time_percentage": 35, "why_inefficient": "每份简历平均耗时3-5分钟，80%的简历在初筛阶段被淘汰，大量时间浪费在不合格简历上"},
        "information_movement": {"description": "候选人信息需要在多个系统间重复录入，从招聘网站导出到ATS，再同步到OA审批", "step_numbers": [2, 3, 7], "time_percentage": 20, "why_inefficient": "重复的数据录入容易出错，且每次切换系统都需要重新查找信息"},
        "judgment_cost": {"description": "面试评估依赖面试官主观判断，缺乏统一的评估标准和辅助工具", "step_numbers": [5, 6], "time_percentage": 15, "why_inefficient": "不同面试官的评估尺度差异大，且需要花时间回忆候选人表现来填写评估表"},
        "communication_cost": {"description": "需要反复与业务部门、候选人沟通面试时间、反馈结果，邮件和微信来回切换", "step_numbers": [4, 5, 6, 8], "time_percentage": 20, "why_inefficient": "协调多个参与方的时间成本高，经常出现爽约或时间冲突需要重新安排"},
        "audit_cost": {"description": "offer审批和背景调查需要层层人工审核，每个环节都要准备材料等待批复", "step_numbers": [7], "time_percentage": 10, "why_inefficient": "审批流程长，且需要人工核对各项信息是否符合公司政策"}
    },
    "agent_flow": {
        "new_process_description": "Agent 智能招聘助手接管简历初筛、面试协调、信息同步等重复性工作，人类专注于面试决策等高价值环节",
        "intervention_points": [
            {"step_number": 3, "intervention_type": "完全自动", "description": "Agent 自动解析简历、匹配JD、生成初筛报告，直接输出建议面试名单", "risk_control": "AI筛选通过率异常时触发人工复核"},
            {"step_number": 4, "intervention_type": "Agent辅助", "description": "Agent 自动协调面试官和候选人时间，智能推荐最佳时间窗", "risk_control": "关键岗位面试安排需要人工确认"},
            {"step_number": 5, "intervention_type": "Agent辅助", "description": "Agent 提供实时面试提示、候选人背景速查、面试问题建议", "risk_control": "评估结果由面试官最终确认"},
            {"step_number": 7, "intervention_type": "完全自动", "description": "Agent 自动进行背调信息核对、生成审批材料、跟踪审批进度", "risk_control": "大额offer需要多级审批"}
        ],
        "human_approval": [
            {"step": 3, "reason": "确认AI筛选结果合理，避免错过特殊人才", "condition": "当AI筛选通过率低于10%或高于50%时触发人工复核"},
            {"step": 6, "reason": "终面决策和offer发放必须由人类做出", "condition": "所有终面通过的候选人均需HR和业务负责人双重复核"}
        ],
        "agent_value_proposition": [
            "人工重复工作减少80%：简历初筛由AI接管，每天可处理1000+份简历",
            "信息搬运成本降为0：各系统间自动同步，无需人工重复录入",
            "判断质量提升40%：AI提供结构化评估框架和历史数据参考",
            "沟通效率提升60%：智能日程协调，自动发送提醒和反馈",
            "审核速度加快70%：自动准备审批材料，实时跟踪进度"
        ],
        "product_solution": {
            "product_name": "智能招聘助手",
            "core_features": [
                "简历自动解析与初筛",
                "智能人岗匹配",
                "面试日程自动协调",
                "面试辅助与评估",
                "Offer自动生成与审批"
            ],
            "user_stories": [
                "作为HR，我希望系统自动筛选简历，节省时间",
                "作为面试官，我希望获得候选人背景速查和面试建议",
                "作为候选人，我希望获得及时的面试安排和反馈"
            ],
            "tech_architecture": "采用前后端分离架构，前端使用React，后端使用Python Flask，集成Anthropic Claude API，对接ATS系统"
        },
        "mvp_plan": [
            {"day": 1, "phase": "准备期", "task": "梳理现有招聘流程，确定MVP对接的3个核心系统（ATS、邮箱、OA）", "deliverable": "需求规格说明书、系统对接清单", "success_metric": "完成所有需求文档评审", "owner": "产品经理", "tools_used": "流程图工具、接口文档"},
            {"day": 2, "phase": "对接期", "task": "实现ATS简历解析接口对接，训练简单的JD匹配模型", "deliverable": "简历解析API、匹配测试报告", "success_metric": "简历解析准确率达到95%", "owner": "AI工程师", "tools_used": "Python、NLP模型"},
            {"day": 3, "phase": "对接期", "task": "开发智能日程协调模块，对接日历和邮件系统", "deliverable": "日程协调服务、邮件通知模块", "success_metric": "能成功为5个候选人安排面试时间", "owner": "后端工程师", "tools_used": "Google Calendar API、邮件服务"},
            {"day": 4, "phase": "测试期", "task": "在测试环境端到端测试，用真实历史简历验证效果", "deliverable": "测试报告、问题修复清单", "success_metric": "核心流程无P0/P1级bug", "owner": "测试工程师", "tools_used": "测试用例管理、缺陷跟踪"},
            {"day": 5, "phase": "优化期", "task": "基于测试反馈优化匹配算法，完善用户界面", "deliverable": "优化后的系统、用户手册", "success_metric": "用户满意度评分达到4.0/5.0", "owner": "全团队", "tools_used": "用户反馈问卷、A/B测试"},
            {"day": 6, "phase": "上线期", "task": "灰度发布，选择1个业务部门进行试点", "deliverable": "上线部署文档、试点运行报告", "success_metric": "成功处理10个真实职位的招聘", "owner": "运维工程师+招聘经理", "tools_used": "部署工具、监控系统"},
            {"day": 7, "phase": "总结期", "task": "收集试点数据，计算ROI，制定全量推广计划", "deliverable": "MVP总结报告、全量推广roadmap", "success_metric": "明确回本周期和第一年ROI", "owner": "项目经理", "tools_used": "数据分析工具、PPT"}
        ]
    },
    "cost": {
        "assumptions": [
            "招聘助理月薪：6000元，每小时成本约35元（按每月172小时计算）",
            "招聘专员月薪：8000元，每小时成本约46元",
            "招聘经理月薪：15000元，每小时成本约87元",
            "月均处理简历数：1000份，月均成功招聘20人",
            "每招1人的平均耗时：简历筛选10小时+面试协调5小时+面试8小时+背调offer4小时=27小时",
            "现有团队配置：2名招聘助理+2名招聘专员+1名招聘经理"
        ],
        "current_cost_detail": {
            "labor_cost_breakdown": [
                {"role": "招聘助理", "monthly_salary": 6000, "hourly_cost": 35, "time_per_application": 15, "cost_per_application": 525, "monthly_volume": 1000, "monthly_cost": 12000},
                {"role": "招聘专员", "monthly_salary": 8000, "hourly_cost": 46, "time_per_application": 8, "cost_per_application": 368, "monthly_volume": 1000, "monthly_cost": 16000},
                {"role": "招聘经理", "monthly_salary": 15000, "hourly_cost": 87, "time_per_application": 4, "cost_per_application": 348, "monthly_volume": 1000, "monthly_cost": 15000}
            ],
            "total_monthly_cost": 43000,
            "total_annual_cost": 516000
        },
        "agent_cost_detail": {
            "api_cost_per_unit": 0.5,
            "setup_cost": 50000,
            "maintenance_cost": 3000,
            "remaining_human_cost": {
                "role": "招聘专员",
                "headcount": 1,
                "monthly_cost": 8000
            },
            "total_monthly_cost": 11500,
            "total_annual_cost": 188000
        },
        "savings": {"monthly_savings": 31500, "annual_savings": 378000},
        "roi": {"break_even_months": 2, "first_year_roi": 656}
    },
    "evidence_urls": [{"title": "企业招聘流程最佳实践", "url": "https://example.com/hr1"}, {"title": "AI招聘效率研究报告", "url": "https://example.com/hr2"}]
}

INSURANCE_DATA = {
    "name": "保险公司理赔处理流程",
    "short_name": "保险理赔",
    "workflow_name": "保险公司理赔处理流程",
    "industry": "保险行业",
    "trigger_condition": "客户发生保险事故，通过电话/APP报案",
    "trigger": "客户发生保险事故，通过电话/APP报案",
    "roles": ["客服代表", "理赔专员", "查勘员", "定损员", "核赔师", "客户"],
    "systems": ["核心业务系统", "查勘APP", "定损系统", "OA审批系统", "支付系统"],
    "metrics": {"steps": 9, "saving": "126.5万", "roi": "482%", "payback": "3个月"},
    "steps": [
        {"step_number": 1, "description": "客户报案与信息登记", "role": "客服代表", "input": "客户来电/APP报案信息", "output": "报案记录与案件编号", "system": "核心业务系统", "estimated_duration_minutes": 20, "is_decision": False},
        {"step_number": 2, "description": "案件分类与派单", "role": "理赔专员", "input": "报案记录", "output": "查勘任务派单", "system": "核心业务系统", "estimated_duration_minutes": 15, "is_decision": False},
        {"step_number": 3, "description": "现场查勘与取证", "role": "查勘员", "input": "查勘任务", "output": "查勘报告与现场照片", "system": "查勘APP", "estimated_duration_minutes": 90, "is_decision": False},
        {"step_number": 4, "description": "损失核定与定损", "role": "定损员", "input": "查勘报告", "output": "定损报告与核价单", "system": "定损系统", "estimated_duration_minutes": 60, "is_decision": True},
        {"step_number": 5, "description": "索赔材料收集", "role": "理赔专员", "input": "客户提交的材料", "output": "完整索赔材料包", "system": "核心业务系统", "estimated_duration_minutes": 30, "is_decision": False},
        {"step_number": 6, "description": "理赔审核", "role": "核赔师", "input": "定损报告与索赔材料", "output": "理赔审核意见", "system": "核心业务系统", "estimated_duration_minutes": 45, "is_decision": True},
        {"step_number": 7, "description": "上级复核（大额案件）", "role": "理赔经理", "input": "审核意见", "output": "复核通过/退回", "system": "OA审批系统", "estimated_duration_minutes": 30, "is_decision": True},
        {"step_number": 8, "description": "赔款计算与支付", "role": "理赔专员", "input": "复核通过的案件", "output": "赔款支付凭证", "system": "支付系统", "estimated_duration_minutes": 20, "is_decision": False},
        {"step_number": 9, "description": "通知客户与归档", "role": "客服代表", "input": "支付凭证", "output": "客户通知与案件归档", "system": "核心业务系统", "estimated_duration_minutes": 10, "is_decision": False}
    ],
    "pain_points": {
        "manual_repetition": {"description": "大量重复录入客户信息、事故信息、索赔信息，同一数据在多个系统间重复输入", "step_numbers": [1, 3, 5], "time_percentage": 30, "why_inefficient": "大量数据重复录入工作，消耗30%的人力时间"},
        "information_movement": {"description": "案件材料在多个环节间流转，从客服到查勘、定损、核赔，需要反复查询和同步", "step_numbers": [2, 4, 6], "time_percentage": 25, "why_inefficient": "信息传递延迟，案件材料分散，难以形成完整视图"},
        "judgment_cost": {"description": "定损核赔依赖专业人员的经验判断，缺乏智能辅助工具，效率和一致性难以保证", "step_numbers": [4, 6], "time_percentage": 20, "why_inefficient": "定损标准难统一，核赔尺度难把握，新手培养周期长"},
        "waiting_cost": {"description": "大量时间在等待状态：等待客户补充材料、等待审核、等待支付", "step_numbers": [5, 7], "time_percentage": 15, "why_inefficient": "客户等待周期长，体验差，案件积压严重"},
        "audit_cost": {"description": "理赔案件需要多级复核、稽核，确保合规，消耗大量管理成本", "step_numbers": [7], "time_percentage": 10, "why_inefficient": "合规压力大，但人工审核效率低，难以覆盖所有案件"}
    },
    "agent_flow": {
        "new_process_description": "智能理赔助手接管报案登记、自动查勘辅助、智能定损、自动核赔，人类专注疑难案件处理",
        "intervention_points": [
            {"step_number": 1, "intervention_type": "完全自动", "description": "智能语音+NLP自动理解报案意图，自动生成报案记录", "risk_control": "复杂案件需要人工确认"},
            {"step_number": 3, "intervention_type": "Agent辅助", "description": "AR/AI辅助查勘，自动识别现场、自动生成查勘报告", "risk_control": "关键证据需要人工审核"},
            {"step_number": 4, "intervention_type": "完全自动", "description": "AI智能定损，图像识别损失，自动匹配配件价格库", "risk_control": "定损金额超过5000元需要人工确认"},
            {"step_number": 6, "intervention_type": "完全自动", "description": "规则引擎自动审核小额案件，大额案件标注风险点", "risk_control": "异常案件触发人工复核"},
            {"step_number": 8, "intervention_type": "完全自动", "description": "自动计算赔款、自动触发支付流程", "risk_control": "大额支付需要多级授权"}
        ],
        "agent_value_proposition": [
            "人工重复工作减少75%：报案登记、数据录入、材料整理自动化",
            "查勘定损效率提升60%：AI辅助查勘、智能定损，标准统一",
            "自动核赔覆盖80%：小额简单案件自动审核，人类只处理20%疑难案件",
            "客户等待周期缩短50%：自动处理、实时反馈、智能提醒补件",
            "合规成本降低40%：AI自动校验规则，全流程可追溯"
        ],
        "product_solution": {
            "product_name": "智能理赔助手",
            "core_features": [
                "智能报案登记",
                "AI辅助查勘",
                "智能定损",
                "自动核赔",
                "智能客服"
            ],
            "user_stories": [
                "作为查勘员，我希望获得AI辅助定损建议",
                "作为核赔师，我希望系统自动审核简单案件",
                "作为客户，我希望实时了解理赔进度"
            ],
            "tech_architecture": "采用微服务架构，集成图像识别、NLP、规则引擎等能力，对接核心业务系统"
        },
        "mvp_plan": [
            {"day": 1, "phase": "准备期", "task": "梳理理赔流程，确定MVP对接核心系统，选择1个试点险种", "deliverable": "需求规格说明书、试点方案", "success_metric": "完成流程梳理和需求评审", "owner": "产品经理", "tools_used": "流程图工具、访谈纪要"},
            {"day": 2, "phase": "对接期", "task": "实现报案自动登记模块，接入语音识别和NLP理解报案意图", "deliverable": "报案登记API、准确率测试报告", "success_metric": "报案信息自动提取准确率90%", "owner": "AI工程师", "tools_used": "语音识别API、NLP模型"},
            {"day": 3, "phase": "对接期", "task": "开发简易智能定损功能，基于历史数据训练基础定损模型", "deliverable": "定损模型API、定损测试报告", "success_metric": "基础定损准确率85%", "owner": "数据工程师", "tools_used": "机器学习框架"},
            {"day": 4, "phase": "测试期", "task": "端到端测试，用历史案件回测效果，收集反馈", "deliverable": "测试报告、问题清单", "success_metric": "核心流程无阻塞性bug", "owner": "测试工程师", "tools_used": "测试管理工具"},
            {"day": 5, "phase": "优化期", "task": "基于测试反馈优化算法，完善界面", "deliverable": "优化后的系统、用户手册", "success_metric": "用户满意度评分达到4.0/5.0", "owner": "全团队", "tools_used": "用户反馈问卷"},
            {"day": 6, "phase": "上线期", "task": "灰度发布，试点运行", "deliverable": "上线报告、试点数据", "success_metric": "成功处理50个试点案件", "owner": "运维+业务团队", "tools_used": "监控系统"},
            {"day": 7, "phase": "总结期", "task": "分析数据，计算ROI，制定推广计划", "deliverable": "MVP总结报告、推广roadmap", "success_metric": "明确回本周期和ROI", "owner": "项目经理", "tools_used": "数据分析工具"}
        ]
    },
    "cost": {
        "assumptions": [
            "理赔专员月薪：7500元，每小时成本约44元（按每月172小时计算）",
            "查勘员月薪：8000元，每小时成本约46元",
            "定损/核赔师月薪：12000元，每小时成本约70元",
            "月均处理案件数：800件，单件平均处理成本620元",
            "单件平均耗时：报案0.5小时+查勘1.5小时+定损1小时+审核0.8小时=3.8小时",
            "现有团队配置：4客服+6查勘+4理赔+3核赔"
        ],
        "current_cost_detail": {
            "labor_cost_breakdown": [
                {"role": "客服代表", "monthly_salary": 6000, "hourly_cost": 35, "time_per_application": 0.5, "cost_per_application": 17, "monthly_volume": 800, "monthly_cost": 24000},
                {"role": "查勘员", "monthly_salary": 8000, "hourly_cost": 46, "time_per_application": 1.5, "cost_per_application": 69, "monthly_volume": 800, "monthly_cost": 48000},
                {"role": "理赔/核赔师", "monthly_salary": 12000, "hourly_cost": 70, "time_per_application": 1.8, "cost_per_application": 126, "monthly_volume": 800, "monthly_cost": 84000}
            ],
            "total_monthly_cost": 156000,
            "total_annual_cost": 1872000
        },
        "agent_cost_detail": {
            "api_cost_per_unit": 1.5,
            "setup_cost": 120000,
            "maintenance_cost": 8000,
            "remaining_human_cost": {
                "role": "理赔/核赔师",
                "headcount": 2,
                "monthly_cost": 24000
            },
            "total_monthly_cost": 33200,
            "total_annual_cost": 518400
        },
        "savings": {"monthly_savings": 122800, "annual_savings": 1473600},
        "roi": {"break_even_months": 1, "first_year_roi": 1128}
    },
    "evidence_urls": [{"title": "保险理赔流程优化案例", "url": "https://example.com/ins1"}, {"title": "AI定损技术白皮书", "url": "https://example.com/ins2"}]
}

ECOMMERCE_DATA = {
    "name": "电商售后纠纷处理流程",
    "short_name": "电商售后",
    "workflow_name": "电商售后纠纷处理流程",
    "industry": "电商零售行业",
    "trigger_condition": "客户收到商品后不满意，申请退换货/退款",
    "trigger": "客户收到商品后不满意，申请退换货/退款",
    "roles": ["在线客服", "售后专员", "仓库管理员", "财务专员", "客户"],
    "systems": ["客服系统", "订单系统", "仓储管理系统", "财务系统", "支付平台"],
    "metrics": {"steps": 7, "saving": "94.8万", "roi": "398%", "payback": "2.5个月"},
    "steps": [
        {"step_number": 1, "description": "客户申请售后/客服介入", "role": "在线客服", "input": "客户在线申请", "output": "售后工单创建", "system": "客服系统", "estimated_duration_minutes": 15, "is_decision": False},
        {"step_number": 2, "description": "审核售后申请", "role": "售后专员", "input": "售后工单", "output": "审核结果（通过/驳回/补充）", "system": "订单系统", "estimated_duration_minutes": 20, "is_decision": True},
        {"step_number": 3, "description": "通知客户寄回商品", "role": "在线客服", "input": "审核通过通知", "output": "客户通知与寄回地址", "system": "客服系统", "estimated_duration_minutes": 10, "is_decision": False},
        {"step_number": 4, "description": "仓库收货与质检", "role": "仓库管理员", "input": "客户寄回商品", "output": "收货与质检报告", "system": "仓储管理系统", "estimated_duration_minutes": 30, "is_decision": False},
        {"step_number": 5, "description": "退款/换货处理", "role": "售后专员", "input": "质检报告", "output": "退款申请/换货安排", "system": "订单系统", "estimated_duration_minutes": 20, "is_decision": False},
        {"step_number": 6, "description": "财务审核与支付", "role": "财务专员", "input": "退款申请", "output": "退款完成", "system": "财务系统/支付平台", "estimated_duration_minutes": 25, "is_decision": True},
        {"step_number": 7, "description": "通知客户与工单归档", "role": "在线客服", "input": "退款完成通知", "output": "客户通知与工单归档", "system": "客服系统", "estimated_duration_minutes": 10, "is_decision": False}
    ],
    "pain_points": {
        "information_movement": {"description": "客户信息、订单信息、物流信息分散在不同系统，需要客服在多个系统间切换查询", "step_numbers": [1, 2, 5], "time_percentage": 35, "why_inefficient": "客服处理一个工单可能要切换5-7个系统，每个工单平均浪费10分钟"},
        "manual_repetition": {"description": "大量工单审核、状态更新、通知发送等机械性重复工作", "step_numbers": [2, 3, 7], "time_percentage": 25, "why_inefficient": "标准化操作占比70%，消耗大量人力"},
        "waiting_cost": {"description": "大量等待环节：等待客户寄回、等待仓库收货、等待财务处理，整体周期长", "step_numbers": [3, 4, 6], "time_percentage": 20, "why_inefficient": "客户等待周期长，体验差，咨询工单增加"},
        "judgment_cost": {"description": "售后审核需要人工判断是否符合售后政策，缺乏统一标准和智能辅助", "step_numbers": [2], "time_percentage": 15, "why_inefficient": "审核尺度不一，有漏判错判，也有过度审核"},
        "audit_cost": {"description": "简单问题升级到高级客服处理，处理成本增加", "step_numbers": [7], "time_percentage": 5, "why_inefficient": "20%的简单问题升级，造成高级客服资源浪费"}
    },
    "agent_flow": {
        "new_process_description": "智能售后助手接管订单自动审核、状态自动同步、客户自动通知，人类只处理例外和纠纷",
        "intervention_points": [
            {"step_number": 1, "intervention_type": "Agent辅助", "description": "AI客服辅助处理咨询，自动回答常见问题，引导自助申请", "risk_control": "投诉升级触发人工"},
            {"step_number": 2, "intervention_type": "完全自动", "description": "规则引擎自动审核售后申请，自动判断是否符合售后政策", "risk_control": "订单金额超过500元需要人工确认"},
            {"step_number": 3, "intervention_type": "完全自动", "description": "自动通知客户，提供寄回地址与快递指引", "risk_control": "无"},
            {"step_number": 4, "intervention_type": "Agent辅助", "description": "OCR自动识别快递单号，智能验收与登记", "risk_control": "异常件需要人工确认"},
            {"step_number": 5, "intervention_type": "完全自动", "description": "自动触发退款/换货流程，自动同步系统状态", "risk_control": "无"},
            {"step_number": 7, "intervention_type": "完全自动", "description": "自动通知客户处理结果，自动归档工单", "risk_control": "无"}
        ],
        "agent_value_proposition": [
            "自动审核覆盖85%：标准售后申请自动审核，无需人工介入",
            "信息查询时间减少70%：系统自动打通，客服不用再切换系统",
            "响应速度缩短80%：自动通知、自动处理，客户无需等待",
            "人力成本降低60%：85%标准化工作自动化，团队规模精简",
            "客户满意度提升40%：快速响应、透明进度、自助服务"
        ],
        "product_solution": {
            "product_name": "智能售后助手",
            "core_features": [
                "AI智能客服",
                "售后自动审核",
                "系统自动打通",
                "进度自动通知",
                "数据分析仪表盘"
            ],
            "user_stories": [
                "作为客服，我希望系统自动回答常见问题",
                "作为客户，我希望自助申请售后并实时查看进度",
                "作为运营，我希望获得售后数据分析报告"
            ],
            "tech_architecture": "基于RPA+AI技术，打通客服、订单、仓储、财务系统，实现自动化处理"
        },
        "mvp_plan": [
            {"day": 1, "phase": "准备期", "task": "梳理售后流程，整理售后规则，选择试点品类", "deliverable": "流程文档、规则清单、试点方案", "success_metric": "完成规则梳理和需求评审", "owner": "产品经理", "tools_used": "流程图工具"},
            {"day": 2, "phase": "对接期", "task": "实现售后自动审核规则引擎，配置基础审核规则", "deliverable": "规则引擎配置、测试用例", "success_metric": "自动审核准确率90%", "owner": "后端工程师", "tools_used": "规则引擎"},
            {"day": 3, "phase": "对接期", "task": "实现系统数据打通，从客服到订单到仓储系统自动同步", "deliverable": "API对接文档、同步服务", "success_metric": "数据实时自动同步", "owner": "后端工程师", "tools_used": "API网关"},
            {"day": 4, "phase": "测试期", "task": "端到端测试，用历史工单回测效果，收集反馈", "deliverable": "测试报告、问题清单", "success_metric": "核心流程无阻塞bug", "owner": "测试工程师", "tools_used": "测试管理工具"},
            {"day": 5, "phase": "优化期", "task": "基于测试反馈优化算法，完善界面", "deliverable": "优化后的系统、用户手册", "success_metric": "用户满意度评分达到4.0/5.0", "owner": "全团队", "tools_used": "用户反馈问卷"},
            {"day": 6, "phase": "上线期", "task": "灰度发布，选择1个品类进行试点", "deliverable": "上线报告、试点数据", "success_metric": "成功处理300个试点工单", "owner": "运维+业务团队", "tools_used": "监控系统"},
            {"day": 7, "phase": "总结期", "task": "分析数据，计算ROI，制定推广计划", "deliverable": "MVP总结报告、推广roadmap", "success_metric": "明确ROI和改进方向", "owner": "项目经理", "tools_used": "数据分析工具"}
        ]
    },
    "cost": {
        "assumptions": [
            "在线客服月薪：5500元，每小时成本约32元（按每月172小时计算）",
            "售后专员月薪：7000元，每小时成本约41元",
            "月均售后工单：4000件，单件平均处理成本158元",
            "单件平均耗时：客服沟通15分钟+审核20分钟+通知10分钟=45分钟",
            "现有团队配置：8在线客服+6售后专员"
        ],
        "current_cost_detail": {
            "labor_cost_breakdown": [
                {"role": "在线客服", "monthly_salary": 5500, "hourly_cost": 32, "time_per_application": 0.3, "cost_per_application": 10, "monthly_volume": 4000, "monthly_cost": 44000},
                {"role": "售后专员", "monthly_salary": 7000, "hourly_cost": 41, "time_per_application": 0.8, "cost_per_application": 33, "monthly_volume": 4000, "monthly_cost": 42000}
            ],
            "total_monthly_cost": 86000,
            "total_annual_cost": 1032000
        },
        "agent_cost_detail": {
            "api_cost_per_unit": 0.3,
            "setup_cost": 80000,
            "maintenance_cost": 5000,
            "remaining_human_cost": {
                "role": "售后专员",
                "headcount": 2,
                "monthly_cost": 14000
            },
            "total_monthly_cost": 20200,
            "total_annual_cost": 282400
        },
        "savings": {"monthly_savings": 65800, "annual_savings": 789600},
        "roi": {"break_even_months": 1.2, "first_year_roi": 887}
    },
    "evidence_urls": [{"title": "电商售后服务白皮书", "url": "https://example.com/ecom1"}, {"title": "AI客服效率报告", "url": "https://example.com/ecom2"}]
}

CUSTOMER_SERVICE_DATA = {
    "name": "客服退款处理流程",
    "short_name": "客服退款",
    "workflow_name": "客服退款处理流程",
    "industry": "客户服务行业",
    "trigger_condition": "客户提出退款申请或投诉",
    "trigger": "客户提出退款申请或投诉",
    "roles": ["一线客服", "客服主管", "财务专员", "客户"],
    "systems": ["CRM系统", "客服系统", "财务系统", "订单系统"],
    "metrics": {"steps": 6, "saving": "58.6万", "roi": "425%", "payback": "2个月"},
    "steps": [
        {"step_number": 1, "description": "客户发起退款申请/投诉", "role": "一线客服", "input": "客户沟通记录", "output": "退款工单创建", "system": "客服系统", "estimated_duration_minutes": 15, "is_decision": False},
        {"step_number": 2, "description": "一线客服审核与沟通", "role": "一线客服", "input": "退款工单", "output": "初审结果与客户沟通记录", "system": "客服系统", "estimated_duration_minutes": 25, "is_decision": True},
        {"step_number": 3, "description": "主管审批（如需要）", "role": "客服主管", "input": "初审结果", "output": "审批意见", "system": "CRM系统", "estimated_duration_minutes": 15, "is_decision": True},
        {"step_number": 4, "description": "订单信息核实与退款金额计算", "role": "一线客服", "input": "审批意见", "output": "退款金额确认", "system": "订单系统", "estimated_duration_minutes": 20, "is_decision": False},
        {"step_number": 5, "description": "财务审核与退款执行", "role": "财务专员", "input": "退款申请", "output": "退款完成", "system": "财务系统", "estimated_duration_minutes": 30, "is_decision": True},
        {"step_number": 6, "description": "通知客户与工单归档", "role": "一线客服", "input": "退款完成通知", "output": "客户通知与工单归档", "system": "客服系统", "estimated_duration_minutes": 10, "is_decision": False}
    ],
    "pain_points": {
        "information_movement": {"description": "客户信息、订单信息、支付信息分散，每次处理需要跨多个系统查询核实", "step_numbers": [2, 4], "time_percentage": 30, "why_inefficient": "处理一个退款工单平均需要在4-5个系统间切换查询"},
        "manual_repetition": {"description": "大量标准化审核、计算、通知等工作，机械性重复", "step_numbers": [2, 4, 6], "time_percentage": 25, "why_inefficient": "70%以上退款是标准化场景，完全可以自动化"},
        "waiting_cost": {"description": "客户等待财务处理周期长，体验差，催办工单多", "step_numbers": [5], "time_percentage": 15, "why_inefficient": "财务处理周期长，客户反复催办增加客服负担"},
        "judgment_cost": {"description": "退款政策复杂，需要客服记忆大量规则，容易出错", "step_numbers": [2], "time_percentage": 15, "why_inefficient": "政策规则多，新手上手慢，错误率高"},
        "audit_cost": {"description": "简单退款也需要层层审批，处理链路长，效率低", "step_numbers": [3], "time_percentage": 15, "why_inefficient": "不必要的审批消耗大量管理成本"}
    },
    "agent_flow": {
        "new_process_description": "智能退款助手自动查询信息、自动审核、自动计算退款金额、自动通知，人类只处理例外",
        "intervention_points": [
            {"step_number": 1, "intervention_type": "Agent辅助", "description": "AI客服自动理解意图，自动收集必要信息", "risk_control": "投诉升级触发人工"},
            {"step_number": 2, "intervention_type": "完全自动", "description": "自动查询订单与支付信息，规则引擎自动审核退款申请", "risk_control": "退款金额超过200元需要人工确认"},
            {"step_number": 3, "intervention_type": "Agent辅助", "description": "只把需要人工确认的场景推给主管，标注关键点", "risk_control": "涉及补偿的需要人工确认"},
            {"step_number": 4, "intervention_type": "完全自动", "description": "自动计算退款金额，自动生成退款申请单", "risk_control": "无"},
            {"step_number": 5, "intervention_type": "完全自动", "description": "自动推送财务系统，自动跟踪退款进度", "risk_control": "无"},
            {"step_number": 6, "intervention_type": "完全自动", "description": "自动通知客户处理结果，自动归档工单", "risk_control": "无"}
        ],
        "agent_value_proposition": [
            "自动处理覆盖80%：标准退款场景完全自动化",
            "处理周期缩短70%：从平均1.5小时缩短到25分钟",
            "人力成本降低55%：大部分工作AI代劳",
            "客户满意度提升35%：快速响应、透明进度",
            "错误率降低80%：规则引擎严格执行，避免人工疏漏"
        ],
        "product_solution": {
            "product_name": "智能退款助手",
            "core_features": [
                "AI智能客服",
                "退款自动审核",
                "金额自动计算",
                "进度自动通知",
                "数据分析仪表盘"
            ],
            "user_stories": [
                "作为客服，我希望系统自动处理标准退款",
                "作为客户，我希望快速获得退款并了解进度",
                "作为主管，我希望只处理需要审批的特殊场景"
            ],
            "tech_architecture": "基于规则引擎+AI技术，打通客服、订单、财务系统"
        },
        "mvp_plan": [
            {"day": 1, "phase": "准备期", "task": "梳理退款流程，整理退款规则，确定试点范围", "deliverable": "流程文档、规则清单、试点方案", "success_metric": "完成规则梳理和需求评审", "owner": "产品经理", "tools_used": "流程图工具"},
            {"day": 2, "phase": "对接期", "task": "实现系统数据打通，CRM、订单、财务系统信息聚合", "deliverable": "数据聚合API、统一视图", "success_metric": "各系统数据实时聚合展示", "owner": "后端工程师", "tools_used": "API网关"},
            {"day": 3, "phase": "对接期", "task": "开发退款自动审核规则引擎，配置基础审核规则", "deliverable": "规则引擎配置、测试用例", "success_metric": "自动审核准确率95%", "owner": "后端工程师", "tools_used": "规则引擎"},
            {"day": 4, "phase": "测试期", "task": "端到端测试，历史工单回测，收集客服反馈", "deliverable": "测试报告、问题清单", "success_metric": "核心流程无阻塞bug", "owner": "测试工程师", "tools_used": "测试管理工具"},
            {"day": 5, "phase": "优化期", "task": "基于测试反馈优化算法，完善界面", "deliverable": "优化后的系统、用户手册", "success_metric": "用户满意度评分达到4.0/5.0", "owner": "全团队", "tools_used": "用户反馈问卷"},
            {"day": 6, "phase": "上线期", "task": "灰度发布，20%流量走新流程", "deliverable": "上线报告、试点数据", "success_metric": "成功处理200个试点工单", "owner": "运维+业务团队", "tools_used": "监控系统"},
            {"day": 7, "phase": "总结期", "task": "分析试点数据，计算ROI，制定推广计划", "deliverable": "MVP总结报告、推广roadmap", "success_metric": "明确ROI和改进方向", "owner": "项目经理", "tools_used": "数据分析工具"}
        ]
    },
    "cost": {
        "assumptions": [
            "一线客服月薪：5000元，每小时成本约29元（按每月172小时计算）",
            "客服主管月薪：8500元，每小时成本约49元",
            "财务专员月薪：7000元，每小时成本约41元",
            "月均退款工单：2000件，单件平均处理成本132元",
            "单件平均耗时：客服沟通25分钟+审核15分钟+财务30分钟=70分钟",
            "现有团队配置：6一线客服+1主管"
        ],
        "current_cost_detail": {
            "labor_cost_breakdown": [
                {"role": "一线客服", "monthly_salary": 5000, "hourly_cost": 29, "time_per_application": 0.8, "cost_per_application": 23, "monthly_volume": 2000, "monthly_cost": 30000},
                {"role": "客服主管", "monthly_salary": 8500, "hourly_cost": 49, "time_per_application": 0.25, "cost_per_application": 12, "monthly_volume": 2000, "monthly_cost": 8500}
            ],
            "total_monthly_cost": 38500,
            "total_annual_cost": 462000
        },
        "agent_cost_detail": {
            "api_cost_per_unit": 0.2,
            "setup_cost": 60000,
            "maintenance_cost": 3500,
            "remaining_human_cost": {
                "role": "一线客服",
                "headcount": 2,
                "monthly_cost": 10000
            },
            "total_monthly_cost": 13900,
            "total_annual_cost": 206800
        },
        "savings": {"monthly_savings": 24600, "annual_savings": 295200},
        "roi": {"break_even_months": 2.4, "first_year_roi": 425}
    },
    "evidence_urls": [{"title": "客服退款流程优化", "url": "https://example.com/cs1"}, {"title": "AI客服应用案例", "url": "https://example.com/cs2"}]
}

# ==================== 工具函数 ====================

# 预设数据字典（支持中英文key）
PRESETS = {
    "招聘筛选流程": RECRUITMENT_DATA,
    "recruitment": RECRUITMENT_DATA,
    "保险公司理赔处理流程": INSURANCE_DATA,
    "insurance": INSURANCE_DATA,
    "电商售后纠纷处理流程": ECOMMERCE_DATA,
    "ecommerce": ECOMMERCE_DATA,
    "客服退款处理流程": CUSTOMER_SERVICE_DATA,
    "customerservice": CUSTOMER_SERVICE_DATA
}

# 预设关键词列表（用于下拉选择）
PRESET_KEYWORDS = list(PRESETS.keys())


def get_preset(keyword):
    """获取预设数据"""
    return PRESETS.get(keyword, RECRUITMENT_DATA)


def export_to_json(data, filepath):
    """导出到 JSON 文件"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def import_from_json(filepath):
    """从 JSON 文件导入"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_workflow_summary():
    """获取所有预设的摘要信息"""
    summaries = []
    for keyword, data in PRESETS.items():
        summaries.append({
            'keyword': keyword,
            'name': data['name'],
            'industry': data['industry'],
            'steps': data['metrics']['steps'],
            'annual_savings': data['cost']['savings']['annual_savings'],
            'roi': data['cost']['roi']['first_year_roi']
        })
    return summaries


# ==================== 用于调试的主函数 ====================

if __name__ == "__main__":
    print("="*60)
    print("  Workflow Thief Arena - 数据模块")
    print("="*60)
    print()
    print("已加载", len(PRESETS), "个预设工作流：")
    for keyword in PRESET_KEYWORDS:
        data = PRESETS[keyword]
        print(f"  - {keyword}")
        print(f"    行业：{data['industry']}")
        print(f"    步骤：{data['metrics']['steps']}步")
        print(f"    ROI：{data['cost']['roi']['first_year_roi']}%")
        print()

