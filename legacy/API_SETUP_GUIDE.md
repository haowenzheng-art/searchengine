# 火山引擎 API 配置指南

## 当前状态

✅ 已完成的工作:
- 集成真实 Bing 网络搜索
- 创建火山引擎 API 客户端 (llm_client.py)
- 完善 Agent 工作流 (agent_enhanced.py)
- 支持预设数据模式和真实 LLM 模式切换
- 添加错误处理和回退机制
- 更新 Web UI，支持真实 LLM 开关和进度显示

⚠️ API 连接说明:
- 如需使用真实 LLM，需要配置正确的火山引擎 API
- 当前配置的 URL 可能需要调整
- API 不可用时自动回退到预设数据，不影响使用

## 使用方式

### 1. Web UI 模式 (推荐)

双击 `启动WebUI.bat` 或运行:
```bash
python app.py
```

然后访问 http://localhost:5000

**Web UI 功能:**
- ✅ 预设数据快速查看
- ✅ 真实 LLM 分析开关
- ✅ 实时进度显示
- ✅ 完整报告展示
- ✅ Word/JSON/Mermaid 下载

### 2. 预设数据模式 (快速演示)

```bash
# 使用预设数据，不需要 API
python agent_enhanced.py --preset "招聘筛选流程"
```

### 3. 真实 LLM 模式 (需要正确配置 API)

修改 `.env` 文件中的配置，然后运行:

```bash
python agent_enhanced.py "招聘筛选流程"
```

## 如何获取正确的火山引擎 API 配置

### 步骤 1: 获取 API Key

1. 访问火山引擎控制台 (https://console.volcengine.com/)
2. 进入 "方舟" (Ark) 服务
3. 创建 API Key

### 步骤 2: 获取 Endpoint URL

火山引擎的 OpenAI 兼容 API URL 格式:
```
https://ark.cn-beijing.volces.com/api/v3
```

注意：不需要在 BASE_URL 中包含 `/chat/completions`，代码会自动添加。

### 步骤 3: 获取 Model ID

在火山引擎控制台创建推理接入点(Endpoint)后，会获得一个类似 `ep-20241203xxxxxx` 的 ID。

### 步骤 4: 更新 .env 文件

```env
# 火山引擎 API 配置
VOLCENGINE_API_KEY=你的_api_key
BASE_URL=https://ark.cn-beijing.volces.com/api/v3
MODEL_NAME=ep-20241203xxxxxx
```

## 测试 API 配置

修改配置后运行:

```bash
python test_api_integration.py
```

## 架构说明

### 文件结构

```
searchengine/
├── llm_client.py          # 火山引擎 API 客户端
├── web_scraper.py         # 网页抓取模块
├── bing_search.py         # Bing 搜索模块
├── agent_enhanced.py      # 主 Agent 逻辑
├── app.py                 # Flask Web 服务
├── workflow_data.py       # 预设工作流数据
├── config.py              # 配置管理
├── .env                   # 环境变量
├── templates/index.html   # 前端页面
├── 启动WebUI.bat          # Windows 快速启动脚本
└── API_SETUP_GUIDE.md     # 本文档
```

### 工作流程

1. 用户输入关键词
2. Bing 搜索相关网页
3. 抓取网页内容
4. 调用 LLM 分析工作流 (或使用预设)
5. 生成分析报告 (JSON + Word + Mermaid)
6. 展示结果

## Web UI 使用说明

1. **选择预设**: 点击预设按钮快速查看示例数据
2. **输入关键词**: 自定义搜索任意工作流
3. **真实 LLM 开关**: 
   - 开启 = 调用火山引擎 API 分析
   - 关闭 = 使用预设数据 (快速演示)
4. **开始分析**: 点击按钮启动分析
5. **查看报告**: 分析完成后展示完整报告
6. **下载文件**: 可下载 JSON/Word/Mermaid 格式

## 故障排查

### API 返回 404

- 检查 BASE_URL 是否正确，应该是 `https://ark.cn-beijing.volces.com/api/v3`
- 不需要在 BASE_URL 中添加 `/chat/completions`

### API 返回 401

- 检查 API Key 是否正确
- 确认 API Key 没有过期

### 其他错误

系统会自动回退到预设数据模式，保证基本功能可用。

## 联系支持

如需要进一步帮助，请检查:
1. 火山引擎官方文档: https://www.volcengine.com/docs/
2. API 控制台: https://console.volcengine.com/
