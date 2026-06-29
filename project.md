# Workflow Discovery Agent - 重构进度追溯

> 本文档追溯从 hackathon 原型到企业级 SaaS 的重构计划执行情况。
> 计划全文：`C:\Users\19802\.claude\plans\sorted-puzzling-noodle.md`
> 旧项目说明（已归档，内容过时）：`legacy/project.md`

## 当前状态

**Phase 0-5 全部完成**，项目可上线 GitHub，可生成产品页面介绍 + 截图。

| Phase | 状态 | 完成日期 | Commit |
|-------|------|---------|--------|
| Phase 0 工程骨架 | ✅ 完成 | 2026-06-26 | 86c8fa9 |
| Phase 1 真 Agent 核心 | ✅ 完成 | 2026-06-26 | deb0091 |
| Phase 2 证据链修复 | ✅ 完成 | 2026-06-26 | ff663d3 |
| Phase 3 SaaS 化 | ✅ 完成 | 2026-06-26 | (会话 A) |
| Phase 4 前端重写 | ✅ 完成 | 2026-06-27 | (会话 B) |
| Phase 5 上线准备 | ✅ 完成 | 2026-06-27 | (会话 B) |

### Phase 3 决策对齐结果

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 多租户方案 | **单租户先行**（用 user_id 隔离，不引入 tenant_id） | 中小企业 SaaS 先跑通业务，多租户复杂度后置。schema 干净，未来要加 tenant_id 只需一次 migration |
| 异步任务队列 | **Celery + Redis**（按原计划） | 长任务（5-10 分钟）必须异步，Celery 5 + Redis broker 是 Python 生态成熟方案 |
| 计费 | **先做用量统计**，Stripe 延后 | 用量记录是计费的基础，先把 usage_records 表做扎实，Stripe 留给 Phase 4/5 |

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

### 单租户先行（不引入 tenant_id）

**决策**：Phase 3 不做多租户隔离，所有业务表用 `user_id` 隔离。

**为什么不做多租户**：
1. 中小企业 SaaS 先跑通业务逻辑比多租户复杂度重要
2. 多租户需要中间件注入 tenant_id filter、JWT 解析 tenant、跨租户测试矩阵——工程量翻倍
3. 当前用户量小（开发期），单租户够用

**未来迁移路径**：所有业务表已有 `user_id`，未来加 `tenant_id` 只需：① 加字段 migration ② 中间件从 JWT 注入 ③ 在 query filter 加 tenant_id 条件。schema 干净，不需要重写。

### 认证：JWT + argon2 + refresh token

**决策**：
- 密码哈希用 argon2-cffi（OWASP 推荐，比 bcrypt 更抗 GPU 暴力）
- JWT 用 HS256 + `jti` 声明（每个 token 唯一，避免同秒生成的 token 相同）
- access token 15min，refresh token 7day
- OAuth2PasswordBearer + OAuth2PasswordRequestForm（Swagger Authorize 按钮可用）

**为什么 access 15min / refresh 7day**：access 短命降低泄露风险，refresh 长命让用户不用频繁登录。refresh 可以黑名单（未来加 `revoked_tokens` 表）。

**为什么 login 不区分用户不存在/密码错**：防枚举攻击。返回相同的 "Incorrect email or password"，不暴露用户是否注册。

**为什么 register 第一个用户自动 admin**：部署后第一个注册的用户是 owner，自动 admin 避免冷启动需要手动改 DB。

### 跨用户隔离：404 而非 403

**决策**：用户 A 访问用户 B 的 workflow，返回 404 而不是 403。

**为什么不返回 403**：403 暴露资源存在性（攻击者知道 workflow_id 存在但不属于自己）。404 不暴露 existence，更安全。

**实现**：`_get_owned_workflow` helper 同时过滤 `workflow_id` 和 `user_id`，查不到返回 404。

### UPSERT 用 PostgreSQL on_conflict_do_update

**决策**：usage_records 表用 `pg_insert.on_conflict_do_update` 实现原子 UPSERT。

**为什么不用 SELECT + INSERT/UPDATE**：并发场景下 SELECT 后另一个请求 INSERT 了相同记录，本请求 UPDATE 时要么报错要么覆盖。UPSERT 是原子的，数据库保证一致性。

**坑**：SQLAlchemy 的 RETURNING 语句会缓存 identity map 里的旧对象。第二次 UPSERT 同一主键时返回的是缓存的对象而不是 DB 里的新值。必须加 `.execution_options(populate_existing=True)` 强制刷新。

**坑**：模型默认 `datetime.utcnow()` 是 naive datetime，service 里如果用 `datetime.now(timezone.utc)` 是 aware，asyncpg 拒绝混合。所有时间戳统一用 `_now_naive_utc()` helper。

### Celery 任务每任务独立 engine

**决策**：Celery worker 里每个任务创建自己的 `create_async_engine + async_sessionmaker`，任务结束 `engine.dispose()`。

**为什么不用全局 engine**：asyncpg connection 绑定 event loop，Celery worker 的 prefork 模型每个子进程有独立 event loop。全局 engine 跨任务复用会报 "Future attached to a different loop"。

**为什么不在 Celery 启动时建 engine**：Celery 的 `worker_init` signal 里的 event loop 跟任务执行的 event loop 不是同一个（prefork 模型）。最简单可靠的就是每任务建一次。

### 测试 fixture：dependency_overrides 路由 get_db

**决策**：测试用 `fastapi_app.dependency_overrides[get_db]` 把 FastAPI 的 get_db 指向 test_engine 的 session_factory。

**为什么不直接用模块级 engine**：模块级 engine 绑定 FastAPI 启动时的 event loop，测试用 httpx.AsyncClient + ASGITransport 在另一个 event loop 跑，跨 loop asyncpg 报 'NoneType' object has no attribute 'send'。

**为什么 test_engine 只在开始时 drop_all + create_all**：结束时 drop_all 会删 alembic 管理的表（如 alembic_version），下次自动生成 migration 会误判所有表需要重建。隔离靠开始时 drop_all 实现。

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
- 准确率 ≥ 85%（CI 阈值）
- 覆盖 4 行业（招聘/保险/电商/客服）× 4 类型（正例/首页/歧义/SEO噪音）
- 跑一次约 4 分钟（30 个 URL 串行 LLM 调用）
- **已知 flaky**：LLM 评分有非确定性，实测准确率在 83-87% 之间波动。Phase 3 跑全量测试时出现过 83.87%（5 个 URL 评分超容差），属于 LLM 噪声而非代码 regression。Phase 4 需要加固定 temperature + seed 或扩到 100 用例降低方差。

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

### Phase 3 验证

**API 单元测试**（34 个，全过）：
- `tests/api/test_auth.py`（14 个）：register（首个 admin / 后续 member / 重复 409 / 短密码 422 / 邮箱格式 422）、login（正确 / 错误密码 / 不存在用户 401）、me（有 token / 无 token 401 / 无效 token 401）、refresh（正常 / access 当 refresh 用 401 / 垃圾 401）
- `tests/api/test_workflows.py`（13 个）：创建 + 入队 Celery、空 query 422、分页列表、status 过滤、详情、不存在 404、删除、**跨用户访问 404**、runs 子资源、evidence 子资源、agent_run + tool_call 查询、错误 run_id 404
- `tests/api/test_usage.py`（5 个）：今日空 / 创建 workflow 后 +1 / 本月包含今日 / completed workflow 完整用量（tool_calls + tokens + search_queries）

**Agent 测试回归**（4 个，全过）：Phase 1 的测试没被破坏。

**Celery worker 验证**：
- 任务注册到 `wda.run_agent_task`，autodiscover 加载 `app.worker.tasks`
- 每任务独立 engine + async_sessionmaker，避免跨 event loop 冲突
- 失败重试 1 次（countdown=10s），再失败标记 workflow.status="failed"
- task_time_limit=600s / soft_time_limit=540s 硬上限

**数据库 migration 验证**：
- `add_users_and_usage_records`：users + api_keys + usage_records 表
- `add_workflows_and_fk_workflow_id`：workflows 表 + 把 agent_runs/evidence 的 workflow_id 从 VARCHAR(64) 改为 INTEGER FK（用 `postgresql_using='workflow_id::integer'` 子句，Postgres 无法自动转换 VARCHAR → INTEGER）

### Phase 4 验证

**前端构建**：
- TypeScript 类型检查通过（`tsc -b` 无错误）
- Vite production build 成功（550KB JS + 22KB CSS，gzip 后 174KB）

**端到端联调**（curl 模拟前端调用）：
- 注册首个用户 → admin ✓
- 登录拿 token ✓
- 创建 workflow → Celery 入队 ✓
- 列表/详情/runs/tool_calls API ✓
- Celery worker 实际跑 agent：8→20 个 tool_calls（search_web → score_evidence → fetch_page → extract_workflow → identify_pain_points → design_agent_flow）

**前端页面**（6 个）：
- Login / Register（react-hook-form + zod 校验）
- Dashboard（分页列表 + 用量卡片 + 状态过滤）
- NewWorkflow（表单 + 示例按钮）
- WorkflowDetail（核心：tool_call 时间线 + 证据链 + 报告 Tab）
- Usage（今日/本月用量卡片）

**关键决策**：
- **跳过 WebSocket，用轮询**：Agent 一步 10-30 秒，2 秒轮询完全够用，实现简单可靠。WebSocket + Redis pub/sub 延后到 V2。
- **shadcn/ui 手写组件**：不装 shadcn CLI，手动创建 10 个基础组件（button/input/card/badge/dialog/dropdown/tabs/progress/separator/avatar/select/skeleton），避免 CLI 引入的配置复杂度。

### Phase 5 验证

**文档**：
- `README.md`：项目介绍 + 快速启动 + 技术栈 + 项目结构
- `docs/deployment.md`：开发环境 + 生产部署 + 端口避让 + 备份 + 故障排查
- `docs/api.md`：所有 REST 端点 + 请求/响应示例 + 状态码 + 工具列表
- `docs/architecture.md`：系统架构 + 9 个核心设计决策 + 数据模型
- `docs/product-pages.md`：10 个产品页面介绍 + 截图位置说明
- `backend/.env.example`：完整环境变量模板

**CI/CD**：
- `.github/workflows/ci.yml`：backend pytest（postgres+redis services）+ frontend build
- push/PR 自动触发

**产品页面截图**：
- `docs/screenshots/` 已补齐核心截图
- 2026-06-29 用真实中文 workflow #18 重新捕获：Dashboard、工作流时间线、证据链、报告页
- 截图尺寸校验：`03-dashboard.png` 1440×900，`05-detail-timeline.png` 1440×1437，`07-evidence.png` 1440×4683，`08-report.png` 1440×2527
- `docs/product-pages.md` 继续作为页面说明和截图索引

### 优化前后真实中文 Workflow 对比（2026-06-29）

用户要求切到 Volc 后跑一条中文 workflow，做真实优化前后对比。查询词统一为 `招聘筛选流程`。

| 指标 | 优化前：串行工具调用（WF #11, Agnes） | 优化后：批量工具 + Volc（WF #18） | 结论 |
|------|--------------------------------------|-----------------------------------|------|
| 状态 | completed | completed | 两者都能完成 |
| 总耗时 | 12m49s | 11m17s | 约 12% 更快 |
| Agent 迭代数 | 18 | 11 | -39%，orchestrator 循环压力明显下降 |
| Tool calls | 18 | 13 | -28%，主要来自 score/fetch 批量化 |
| 输入 tokens | 190,364 | 28,139 | -85%，上下文膨胀被明显压住 |
| 输出 tokens | 10,396 | 18,406 | 报告内容更完整 |
| Tool 总耗时 | 216.2s | 518.3s | Volc 限流 + GLM-5.2 tool retry 拉长工具耗时 |
| 证据链 | 串行 score/fetch | 24 条证据，13 条高分，12 条已抓取 | 覆盖更完整 |

**关键观察**：
1. 批量工具把“6 次 score + 6 次 fetch”压成 `score_evidence_batch` + `fetch_page_batch`，让 Agent 迭代数从 18 降到 11。
2. 输入 tokens 从 190K 降到 28K，是本轮最核心优化；这说明减少 tool-use 轮次比单纯换模型更关键。
3. Volc 有严格 429 限流。#17 曾因并发 5 的 `score_evidence_batch` 失败；已把并发降到 3，并加 2s/4s/8s 指数退避重试。#18 中 `score_evidence_batch` 用时 145.95s 但最终成功，证明重试逻辑生效。
4. GLM-5.2 仍存在 schema 稳定性问题：#18 的 `calculate_roi` 连续 3 次返回 `roi` 字段类型错误，`save_report` 第一次缺 `summary`，orchestrator 继续循环后自愈完成。

**截图产物**：
- `docs/screenshots/03-dashboard.png`
- `docs/screenshots/05-detail-timeline.png`
- `docs/screenshots/07-evidence.png`
- `docs/screenshots/08-report.png`

---

## 当前架构

```
backend/
├── app/
│   ├── main.py                    # FastAPI 入口 + /health + 4 个 router
│   ├── config.py                  # pydantic-settings + AliasChoices (LLM_/VOLC_)
│   ├── core/
│   │   ├── logging.py            # structlog JSON
│   │   └── security.py           # argon2 + JWT + oauth2 + require_role
│   ├── db/                        # async session factory + get_db
│   ├── models/                    # User / Workflow / AgentRun / ToolCall / Evidence / EvidenceFeedback / UsageRecord
│   ├── agent/
│   │   ├── llm.py                 # Anthropic SDK + 火山引擎 base_url
│   │   ├── orchestrator.py        # tool use 主循环 + contextvar 注入
│   │   ├── state.py               # DB 持久化 helper
│   │   ├── prompts.py             # system prompts
│   │   ├── run.py                 # CLI 入口
│   │   └── tools/                 # 8 个 tool + registry
│   ├── search/
│   │   ├── bing_scraper.py        # ddgs 库封装
│   │   ├── fetcher.py             # Playwright + BS4 fallback
│   │   └── scorer.py              # 三层评分
│   ├── usage/
│   │   └── service.py             # UPSERT + record_completion + 聚合查询
│   ├── worker/
│   │   ├── celery_app.py          # Celery 5 配置
│   │   └── tasks.py               # run_agent_task + 每任务独立 engine
│   └── api/v1/
│       ├── auth.py                # register / login / me / refresh
│       ├── workflows.py           # CRUD + runs/evidence/tool_calls 子资源
│       ├── usage.py               # today / month
│       └── feedback.py            # 证据反馈 REST API
├── alembic/                       # 4 个 migration
├── tests/                         # 38 个单元测试
└── .env.example                   # 环境变量模板

frontend/
├── src/
│   ├── pages/                     # Login / Register / Dashboard / NewWorkflow / WorkflowDetail / Usage
│   ├── components/
│   │   ├── AppLayout.tsx          # 顶栏 + 导航 + 用户菜单
│   │   ├── RequireAuth.tsx        # 路由守卫
│   │   ├── ToolCallTimeline.tsx   # Agent 执行时间线（核心）
│   │   ├── WorkflowStatusBadge.tsx
│   │   └── ui/                    # shadcn 基础组件 (10+)
│   ├── stores/auth.ts             # Zustand auth (persist)
│   ├── lib/
│   │   ├── api.ts                 # axios + 拦截器 + refresh
│   │   ├── api-services.ts        # API 调用函数
│   │   ├── types.ts               # TS 类型
│   │   └── utils.ts               # cn + 日期格式化
│   └── App.tsx                    # 路由配置
└── package.json

infra/       # docker-compose.yml (postgres 5433 + redis 6380)
docs/        # deployment.md / api.md / architecture.md / product-pages.md
.github/     # workflows/ci.yml
legacy/      # 旧代码归档，不维护
README.md    # 项目入口
project.md   # 本文档
```

---

## 遗留问题（V2 处理）

1. **SerpAPI key 未用**：`.env` 里 `SERPAPI_KEY` 为空。当前用 ddgs 替代，如果 ddgs 不稳定或要规模化，再考虑 SerpAPI。
2. **知乎反爬**：Playwright + httpx 都拿不到知乎内容（403）。V2 可能要加代理池或用 archive.org fallback。
3. **GLM-5.2 tool use 不稳定**：calculate_roi/save_report schema 偶发失败，orchestrator 能靠继续循环自愈；V2 观察，必要时加 retry 层或换更强模型。
4. **搜索无缓存**：每次都打 ddgs。V2 加 Redis 缓存（query hash → 结果，TTL 1h）。
5. **黄金集只有 30 用例**：计划是 100 个。V2 通过用户反馈闭环扩充。
6. **无 Stripe 计费**：usage_records 表已就绪，V2 接 Stripe 把用量转为账单。
7. **无 WebSocket 实时进度**：当前用 2 秒轮询，UX 良好。V2 如果要毫秒级实时，加 `/workflows/{id}/stream` + Redis pub/sub。
8. **无速率限制**：V2 加 Redis rate limit（免费 10/天，付费按 plan）。
9. **无 refresh token 黑名单**：当前 refresh token 7 天有效期内均可换新。V2 加 `revoked_tokens` 表支持登出。
10. **无多租户**：当前用 user_id 隔离。V2 如果要服务多个组织，加 tenant_id + 中间件。
11. **Volc 429 限流**：评分批量工具已把并发从 5 降到 3，并加入指数退避；V2 可按租户加 Redis rate limit 和 provider 级全局限流。
12. **黄金集 flaky**：LLM 评分非确定性，实测准确率在 83-87% 波动。V2 加固定 temperature + seed 或扩到 100 用例降低方差。

---

## 下一步

项目已补齐真实中文 workflow 基准、截图和 GitHub 文档。建议后续按需进入 V2：
   - Stripe 计费
   - WebSocket 实时进度
   - 多租户
   - 速率限制
   - 黄金集扩充到 100 用例
