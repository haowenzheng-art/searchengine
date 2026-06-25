# Legacy 旧代码归档

本目录保存重构前的原始代码，**仅供对照参考，不再维护**。

## 保留原因

1. **对照参考**：重构期间随时回看旧实现，验证新方案是否真正改进
2. **回归测试**：新 Agent 跑出的结果可以和 `output/` 下的旧输出对比
3. **历史追溯**：保留参赛版本的完整状态

## 旧代码的已知问题（重构要解决的）

- `bing_search.py:52-79` `get_backup_urls` — 抓取失败时返回写死的英文站 URL（SHRM/Forbes/MIT Tech Review），与中文 query 无关
- `llm_client.py:36-44` — URL 硬试三个变体，说明作者自己都没搞清 API endpoint
- `llm_client.py:160-162` — LLM 失败时静默返回预设数据，用户花 API 钱却拿到 fallback
- `agent_enhanced.py:317` `run_full_agent` — 硬编码顺序流水线，LLM 只调用一次，不是真 Agent
- `app.py:131` — Flask debug=True 开在 0.0.0.0:5000，Werkzeug debugger 可执行任意代码
- `config.py:10` — 默认 BASE_URL 是 agnes-ai.com 第三方代理但 README 一直宣称"火山引擎"

## 旧代码结构

| 文件 | 作用 |
|------|------|
| `agent_enhanced.py` | 假装 Agent 的顺序流水线 |
| `app.py` | Flask Web 服务 |
| `bing_search.py` | Bing 网页爬取搜索 + 注水 fallback |
| `llm_client.py` | 火山引擎（实际 agnes-ai 代理）API 客户端 |
| `web_scraper.py` | BeautifulSoup 抓取 |
| `workflow_data.py` | 预设工作流数据 |
| `README.md` | 旧项目说明文档（保留原貌） |
| `templates/index.html` | 旧 Web UI |
| `output/` | 旧分析报告输出（6月3日-6月9日） |
| `.env` | 旧 API 配置（**注意：包含真 API key，已在根 .gitignore 排除，不要提交**） |

## 不做的事

- ❌ 不要在这里修复 bug——所有修复在新代码 `backend/` 里做
- ❌ 不要运行这里的代码——新项目用 `backend/` 的 FastAPI
- ❌ 不要把 `.env` 提交到 git
