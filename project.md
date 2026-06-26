# Workflow Discovery Agent - 重构进度追溯

> 本文档追溯从 hackathon 原型到企业级 SaaS 的重构计划执行情况。
> 计划全文：`C:\Users\19802\.claude\plans\sorted-puzzling-noodle.md`
> 旧项目说明（已归档，内容过时）：`legacy/project.md`

## 当前状态

**Phase 0-2 已完成**，等待用户审查后对齐 Phase 3+ 的 SaaS 架构决策。

| Phase | 状态 | 完成日期 | Commit |
|-------|------|---------|--------|
| Phase 0 工程骨架 | ✅ 完成 | 2026-06-26 | 86c8fa9 |
| Phase 1 真 Agent 核心 | ✅ 完成 | 2026-06-26 | deb0091 |
| Phase 2 证据链修复 | ✅ 完成 | 2026-06-26 | ff663d3 |
| Phase 3 SaaS 化 | ⏸ 暂停待对齐 | - | - |
| Phase 4 前端重写 | ⏸ 暂停待对齐 | - | - |
| Phase 5 上线准备 | ⏸ 暂停待对齐 | - | - |

---

## 关键决策记录

### LLM Provider：火山引擎方舟 Claude 兼容协议（底层 GLM-5.2）

**决策**：用 `https://ark.cn-beijing.volces.com/api/coding` 端点 + Anthropic SDK。

**为什么不是 Anthropic 官方**：用户在中国大陆，国际网络不稳定。火山引擎方舟提供 Claude 兼容协议，tool use 格式完全兼容（验证过：返回 `tool_use` block + `stop_reason="tool_use"`），底层是 GLM-5.2。

**为什么不是火山引擎方舟 OpenAI 兼容协议（/api/v3）**：OpenAI tool use 协议和 Anthropic 不同（`tool_calls` 数组 vs `tool_use` block，tool result 消息格式不同），重写翻译层成本高。Claude 兼容协议直接用现成的 Anthropic SDK。

**配置**：`.env` 里 `VOLC_API_KEY` / `VOLC_BASE_URL` / `VOLC_MODEL`，通过 pydantic AliasChoices 同时支持 `LLM_` 前缀。

**已知问题**：GLM-5.2 的 tool use 质量比 Claude 弱，calculate_roi 工具在集成测试中失败 3 次后才成功（LLM 没按 schema 调用 tool）。orchestrator 靠 max_iterations=20 兜底自愈。如果 Phase 3 发现 tool use 不稳定，可能要加 retry 或 ReAct 兜底。

### 搜索引擎：ddgs 库（DuckDuckGo Search）

**决策**：用 `ddgs` 库，不用 SerpAPI，不用 Bing 爬虫。

**为什么不是 SerpAPI**：$75/月 5000 次，对开发期太贵。

**为什么不是自爬 Bing**：Bing 对中文招聘类 query 默认返回招聘网站首页（zhaopin/zhipin/51job/liepin），而不是流程文章。换 query 变体也没用。

**为什么不是自爬 DuckDuckGo HTML**：DDG 反爬严重，短时间内多次请求触发 anomaly-modal 验证，返回空 HTML。`ddgs` 库内部处理了反爬（随机 UA + 请求间隔），返回真实 URL 不需要解码。

**已知问题**：ddgs 是同步库，用 `asyncio.to_thread` 跑在线程池。如果 Phase 3 高并发，可能要换成异步搜索或加 Redis 缓存（query hash → 结果，TTL 1h）。

### 三层证据评分架构

**决策**：Layer 1 规则（免费）→ Layer 2 Haiku（$0.001）→ Layer 3 Sonnet（$0.01，仅 4-6 分边界）。

**为什么必须有 Layer 1**：legacy 项目的证据链 8 个 URL 中 6 个是首页、2 个歧义命中——这些根本不该进 LLM 评估。规则砍掉 60-70% 明显垃圾，省钱省时间。

**为什么 Layer 3 只跑 4-6 分**：高分（≥7）和低分（≤3）Layer 2 已经够准，边界 case 才需要更强模型复评。实测 Layer 3 把一个 CSDN 文章从 6.0 升到 8.0（确实讲招聘流程七步骤），证明边界复评有价值。

**为什么用 tool_use 强制 JSON**：不靠 prompt 自觉输出 JSON，用 Anthropic SDK 的 `tool_choice` 强制模型调用一个 response tool，schema 由 pydantic 定义。避免 LLM 输出格式不稳定。

### 数据库端口避让

**决策**：postgres 用 5433，redis 用 6380，不用默认 5432/6379。

**为什么**：用户机器上 `mediapilot-redis`（6379）和 `jobhunter-postgres`（5432）已在运行，不能停。避让端口避免冲突。

### ORM：SQLAlchemy 2.0 async + Alembic

**决策**：runtime 用 asyncpg，migration 用 psycopg3。

**为什么不用同步 ORM**：FastAPI 是异步框架，LLM 调用 + 抓取都是 IO 密集，async 让并发更高。

**为什么 migration 用 psycopg3 而不是 asyncpg**：Alembic 的 sync migration 更稳定，async migration 文档少、坑多。`env.py` 把 `postgresql+asyncpg://` 替换成 `postgresql+psycopg://` 跑同步 migration。

**已知问题**：测试 fixture 必须用 function-scoped（不能 session-scoped），因为 asyncpg 绑定 event loop，跨 loop 复用会报 "Future attached to a different loop"。

### 证据持久化：每个 tool_call 写 DB

**决策**：orchestrator 每执行一个 tool_use block 就写一条 `tool_calls` 记录。

**为什么**：调试（看 LLM 调了什么 tool）、审计（用户投诉时追溯）、计费（按 token 收费）都依赖这个。集成测试验证了 16 次 tool 调用全部持久化。

### 断点续跑：messages 存 JSONB

**决策**：`agent_runs.messages` 字段存完整 Anthropic messages 历史。

**为什么**：长任务（5-10 分钟）可能被进程崩溃打断。重启后从 DB 读 messages，传 `resume_from=agent_run_id` 给 orchestrator 继续跑。

**已知坑**：SQLAlchemy 的 JSONB 不检测原地修改（`agent_run.messages.append(...)` 不会触发 UPDATE）。必须 `agent_run.messages = list(messages)` 创建新 list 才会持久化。已在 `state.py:update_agent_run_state` 处理。

---

## 验证结果

### Phase 1 验证

**单元测试**（4 个，全过）：
- `test_happy_path`：4 次 tool 调用后 save_report 完成
- `test_tool_error_persists_and_continues`：tool 失败时 is_error 返回给 LLM，继续
- `test_max_iterations_force_terminates`：达到上限强制 save_report，没调则 failed
- `test_resume_from_interrupted`：从失败的 agent_run 恢复继续

**真实 API 集成测试**（GLM-5.2）：
- 11 轮迭代，16 次 tool 调用
- LLM 自愈了 3 次 calculate_roi 失败 + 1 次 save_report schema 错误
- 最终产出：6 工作流步骤 / 5 痛点 / 6 介入点 / ROI 158%
- 耗时约 12 分钟（GLM-5.2 thinking 模式慢）

### Phase 2 验证

**黄金集测试**（30 用例）：
- 准确率 ≥ 85%（CI 阈值），实测通过
- 覆盖 4 行业（招聘/保险/电商/客服）× 4 类型（正例/首页/歧义/SEO噪音）
- 跑一次约 4 分钟（30 个 URL 串行 LLM 调用）

**端到端冒烟测试**（`scripts/e2e_smoke.py`）：
- 搜索 "招聘筛选流程" 返回 8 个真实文章（知乎/MBA智库/Moka/i人事/CSDN）
- Layer 1 拒绝 1 个首页（zhihuibaoming.com）
- Layer 3 把 1 个边界 case 从 6.0 升到 8.0（CSDN 招聘流程七步骤）
- 6 个 score ≥ 7 的证据成功抓取正文
- 抓取失败 2 个（知乎 403 反爬）—— fetcher 返回 error 给 LLM，不静默 fallback

**反馈 API 测试**：
- POST 提交反馈 ✓
- 重复提交更新已有记录（UNIQUE 约束）✓
- GET 统计 useful_count / not_useful_count ✓

---

## 当前架构

```
backend/
├── app/
│   ├── main.py                    # FastAPI 入口 + /health + feedback router
│   ├── config.py                  # pydantic-settings + AliasChoices
│   ├── core/logging.py            # structlog JSON
│   ├── db/                        # async session factory
│   ├── models/                    # AgentRun / ToolCall / Evidence / EvidenceFeedback
│   ├── agent/
│   │   ├── llm.py                 # Anthropic SDK + 火山引擎 base_url
│   │   ├── orchestrator.py        # tool use 主循环 + contextvar 注入
│   │   ├── state.py               # DB 持久化 helper
│   │   ├── prompts.py             # system prompts
│   │   └── tools/                 # 8 个 tool + registry
│   ├── search/
│   │   ├── bing_scraper.py        # ddgs 库封装（函数名保留兼容）
│   │   ├── fetcher.py             # Playwright + BS4 fallback
│   │   └── scorer.py              # 三层评分
│   └── api/v1/feedback.py        # 证据反馈 REST API
├── alembic/                       # 2 个 migration
├── tests/
│   ├── agent/test_orchestrator.py # 4 个单元测试
│   ├── search/test_golden_set.py  # 黄金集测试
│   └── golden_set/evidence_scores.jsonl  # 30 用例
└── scripts/e2e_smoke.py          # 端到端冒烟测试

frontend/    # Phase 0 初始化，Phase 4 重写
infra/       # docker-compose.yml (postgres 5433 + redis 6380)
legacy/      # 旧代码归档，不维护
docs/        # 空，Phase 5 补 deployment.md / api.md
```

---

## 遗留问题（Phase 3+ 处理）

1. **SerpAPI key 未用**：`.env` 里 `SERPAPI_KEY` 为空。当前用 ddgs 替代，如果 ddgs 不稳定或要规模化，再考虑 SerpAPI。
2. **知乎反爬**：Playwright + httpx 都拿不到知乎内容（403）。Phase 3 可能要加代理池或用 archive.org fallback。
3. **GLM-5.2 tool use 不稳定**：calculate_roi 失败率较高。Phase 3 观察，必要时加 retry 层或换更强模型。
4. **搜索无缓存**：每次都打 ddgs。Phase 3 加 Redis 缓存（query hash → 结果，TTL 1h）。
5. **黄金集只有 30 用例**：计划是 100 个。Phase 3+ 通过用户反馈闭环扩充。
6. **无前端**：Phase 4 重写，Agent 执行可视化是核心卖点。
7. **无多租户/认证**：Phase 3 实现，tenant_id 隔离 + JWT。

---

## 下一步

等待用户审查 Phase 0-2。审查通过后，对齐 Phase 3 的 SaaS 架构决策：
- 多租户隔离方案（tenant_id vs schema-per-tenant）
- 认证方案（JWT + refresh token）
- 异步任务队列（Celery + Redis）
- 是否现在就接 Stripe 还是先做前端
