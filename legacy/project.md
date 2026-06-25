# Workflow Thief Arena - 项目说明

## 一、使用的工具

| 工具/技术 | 用途 | 选型理由 |
|-----------|------|---------|
| **Python 3.9+** | 主要开发语言 | 生态丰富，AI 库支持完善 |
| **Flask** | Web 后端框架 | 轻量易上手，适合快速开发 |
| **Anthropic Claude API** | 大语言模型 | 通过火山引擎接入，推理能力强 |
| **Bing Search API** | 网页搜索 | 搜索结果质量高，有官方 API |
| **BeautifulSoup 4** | 网页内容抓取 | 解析 HTML 简单可靠 |
| **Requests** | HTTP 请求库 | 简单易用，稳定可靠 |
| **python-docx** | Word 文档生成 | 生成格式规范的 docx 文档 |
| **Mermaid** | 流程图渲染 | 文本描述即可生成专业流程图 |
| **HTML/CSS/JavaScript** | 前端界面 | 原生技术，无需框架依赖 |

---

## 二、搭建方式

### 整体架构

```
Workflow Discovery Agent
├── 用户交互层 (Web UI)
│   └── templates/index.html - 可视化界面
├── 业务逻辑层 (Flask Server)
│   └── app.py - API 路由和任务管理
├── Agent 核心层
│   └── agent_enhanced.py - 搜索/抓取/分析/文档生成
└── 数据层
    └── workflow_data.py - 预设工作流数据
```

### 搭建步骤

#### 1. 项目初始化
```bash
# 创建项目目录
mkdir searchengine
cd searchengine

# 初始化虚拟环境（可选）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

#### 2. 安装依赖
```bash
pip install flask requests beautifulsoup4 python-docx anthropic
```

#### 3. 配置文件
创建 `config.py` 存放 API Key：
```python
VOLCENGINE_API_KEY = "your-api-key-here"
BING_API_KEY = "your-bing-key-here"
MODEL = "ep-20241203xxxxxx"
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
```

#### 4. 核心模块开发
- **workflow_data.py**：定义预设工作流数据结构
- **agent_enhanced.py**：实现 Agent 核心逻辑
- **app.py**：实现 Flask Web 服务
- **templates/index.html**：实现前端界面

#### 5. 测试与调试
```bash
# 测试 Agent 核心逻辑
python test_mermaid.py

# 启动 Web 服务
python app.py

# 浏览器访问 http://localhost:5000
```

---

## 三、Agent 流程

### 4 Agent 协作架构

```
用户输入关键词
    ↓
[搜索 Agent] → 搜索互联网 → 发现候选工作流
    ↓
[抓取 Agent] → 抓取网页内容 → 提取文本信息
    ↓
[分析 Agent] → LLM 深度分析 → 识别痛点 + 设计改造方案
    ↓
[文档 Agent] → 生成完整报告 → Word 文档输出
```

### 详细流程说明

#### 阶段 1：搜索与发现 (Search Agent)
**目标**：从互联网找到相关工作流信息

**处理步骤**：
1. 接收用户输入的关键词（如"招聘筛选流程"）
2. 调用 Bing Search API 搜索相关网页
3. 获取前 10-15 个搜索结果
4. 过滤低质量、非相关链接

#### 阶段 2：内容抓取 (Fetch Agent)
**目标**：获取网页实际内容

**处理步骤**：
1. 遍历搜索结果 URL
2. 使用 Requests 下载网页 HTML
3. 使用 BeautifulSoup 解析 HTML
4. 提取正文文本，去除广告、导航等噪音
5. 截断超长文本（保留前 5000 字符）

#### 阶段 3：深度分析 (Analyze Agent)
**目标**：理解流程，识别痛点，设计方案

**处理步骤**：
1. 构建 Prompt，包含抓取内容和分析要求
2. 调用 Anthropic Claude API
3. LLM 输出结构化 JSON，包含：
   - 原始工作流拆解
   - 低效点分析
   - Agent 改造方案
   - 7 天 MVP 计划
   - 成本收益计算
4. 解析 JSON，结构化存储

#### 阶段 4：文档生成 (Document Agent)
**目标**：生成完整的 Word 分析报告

**处理步骤**：
1. 创建 Word 文档对象
2. 按顺序填充 11 个章节
3. 生成 Mermaid 流程图代码
4. 创建数据表格
5. 保存为 .docx 文件

---

## 四、每一步输入输出

### 1. 用户输入 → 搜索 Agent

| 项目 | 内容 |
|------|------|
| **输入** | 关键词字符串（如"企业招聘筛选流程"） |
| **处理** | Bing Search API 搜索 |
| **输出** |
| - 搜索结果列表 |
| - 每个结果包含：标题、URL、摘要 |

### 2. 搜索结果 → 抓取 Agent

| 项目 | 内容 |
|------|------|
| **输入** | URL 列表 |
| **处理** | Requests + BeautifulSoup 抓取 |
| **输出** |
| - 网页纯文本内容 |
| - 证据链 URL 列表 |

### 3. 抓取内容 → 分析 Agent

| 项目 | 内容 |
|------|------|
| **输入** | 网页文本 corpus + 分析 Prompt |
| **处理** | Claude LLM 推理分析 |
| **输出** | 结构化 JSON，包含： |
| - workflow_name - 工作流名称 |
| - industry - 所属行业 |
| - trigger_condition - 触发条件 |
| - roles - 参与角色列表 |
| - steps - 流程步骤（含角色、输入、输出、系统） |
| - pain_points - 低效点分析 |
| - agent_flow - Agent 改造方案 |
| - - intervention_points - 介入点列表 |
| - - human_approval - 人类确认点 |
| - - product_solution - 产品方案 |
| - - mvp_plan - 7 天 MVP 计划 |
| - cost - 成本收益分析 |
| - evidence_urls - 证据链接 |
| - usage - Token 消耗统计 |

### 4. 分析结果 → 文档 Agent

| 项目 | 内容 |
|------|------|
| **输入** | 完整分析 JSON 数据 |
| **处理** | python-docx 生成文档 |
| **输出** |
| - Word 文档 (.docx) |
| - 包含 11 个章节 |
| - 包含 Mermaid 流程图 |
| - 包含数据表格 |

### 5. Web UI 完整流程

| 步骤 | 用户操作 | 系统处理 |
|------|---------|---------|
| 1 | 打开网页 | 加载 index.html |
| 2 | 点击预设按钮/输入关键词 | 准备分析参数 |
| 3 | 点击"开始分析" | 触发后台任务 |
| 4 | 等待分析完成 | 显示进度动画 |
| 5 | 查看结果 | 展示各标签页内容 |
| 6 | 下载文档 | 提供 Word 文件下载 |

---

## 五、设计理念

### 核心理念：第一性原理

不从惯例出发，从问题本质出发：

#### 1. 真实数据驱动
**原则**：基于真实网络信息，而非凭空假设

**实现**：
- 必应搜索真实网页
- BeautifulSoup 抓取实际内容
- 所有证据链保留原始 URL
- 预设数据也基于真实行业流程

**为什么重要**：
- 工作流分析必须基于实际情况
- 避免"想当然"的流程设计
- 有证据链支持，可信度更高

#### 2. ROI 导向
**原则**：每个改造点都要有明确的成本收益分析

**实现**：
- 当前成本详细拆解（月薪、时薪、单耗时间）
- Agent 方案成本建模（API 成本、维护成本、剩余人力）
- 月度/年度节省计算
- 回本周期和 ROI 指标
- 7 天 MVP 验证计划，快速验证假设

**为什么重要**：
- 企业决策需要量化数据
- 避免为了自动化而自动化
- 有限资源优先投入高 ROI 项目

#### 3. 渐进式落地
**原则**：不追求完美，快速验证，小步快跑

**实现**：
- 7 天 MVP 计划，每天有明确交付物
- 每个阶段有量化成功指标
- 第 6 天邀请真实用户测试
- 第 7 天总结并决策是否继续

**为什么重要**：
- 降低风险：不用等 6 个月才发现方向错了
- 快速学习：真实用户反馈最宝贵
- 团队信心：每一步都有成果，士气更高

#### 4. 人机协作
**原则**：Agent 替代重复工作，人类专注高价值决策

**实现**：
- 明确区分三种介入类型：
  - **完全自动**：Agent 独立完成（简历初筛、信息同步）
  - **Agent 辅助**：Agent 提供辅助，人类主导（面试辅助、查勘辅助）
  - **必须人类确认**：关键决策由人类做出（终面决策、大额赔款）
- 风险控制点：高风险场景必须有人工把关
- 风险控制措施：明确列出每个介入点的风控手段

**为什么重要**：
- 当前技术限制：AI 还不能处理 100% 场景
- 责任归属：关键决策必须有人负责
- 用户体验：人机协同 > 全自动化 > 纯人工

---

## 六、关键设计决策

### 决策 1：用 Mermaid 而非图片流程图
**理由**：
- Mermaid 是文本，易于版本控制
- 可以程序化生成
- 渲染效果专业
- 适合放在 Word/Markdown 中

### 决策 2：提供预设数据 + 自定义搜索
**理由**：
- 预设数据：快速演示，无需 API Key
- 自定义搜索：展示真实能力，满足比赛要求
- 两者结合，兼顾易用性和完整性

### 决策 3：用 Python-docx 而非 PDF
**理由**：
- Word 易于编辑和修改
- 生成代码更简单
- 用户接受度更高
- 可以另存为 PDF

### 决策 4：简化 Mermaid 语法（移除 classDef）
**理由**：
- Mermaid 10.9.6 对 classDef 支持有问题
- 用文字标注更稳定
- 不影响流程图表达能力

---

## 七、项目文件说明

| 文件 | 说明 |
|------|------|
| `agent_enhanced.py` | Agent 核心逻辑（搜索/抓取/分析/文档生成） |
| `app.py` | Flask Web 服务器 |
| `workflow_data.py` | 预设工作流数据 |
| `config.py` | 配置文件（API Key） |
| `requirements.txt` | Python 依赖列表 |
| `templates/index.html` | Web UI 前端界面 |
| `test_mermaid.py` | Mermaid 生成测试脚本 |
| `project.md` | 本文档 - 项目说明 |
| `README.md` | 完整项目文档 |
| `output/` | Word 文档输出目录 |

---

## 八、快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key（可选，可用预设数据）
# 编辑 config.py

# 3. 启动 Web 服务
python app.py

# 4. 浏览器访问
http://localhost:5000
```
