# 架构设计

## 系统总览

```
┌─────────────┐     ┌──────────────────────────────┐
│ React SPA   │────▶│ FastAPI (REST)              │
│ (Vite+TS)   │     │  - JWT auth                  │
└─────────────┘     │  - 跨用户隔离 (404)           │
                    └──────┬───────────────────────┘
                           │
                    ┌──────▼───────────────────────┐
                    │ Celery Worker                │
                    │  ┌────────────────────┐     │
                    │  │ Agent              │     │
                    │  │ Orchestrator       │     │
                    │  │ (Anthropic SDK     │     │
                    │  │  tool use loop)    │     │
                    │  └─────────┬──────────┘     │
                    │   ┌────────┴────────┐        │
                    │   ▼                 ▼        │
                    │ search_web    score_evidence │
                    │   │                 │        │
                    │   ▼                 ▼        │
                    │ fetch_page    extract_workflow│
                    │   │                 │        │
                    │   └────────┬────────┘        │
                    │            ▼                 │
                    │      save_report              │
                    └──────┬───────────────────────┘
                           │
                    ┌──────▼──────┐  ┌─────────┐
                    │ PostgreSQL  │  │ Redis   │
                    │ (user_id)  │  │ (broker)│
                    └─────────────┘  └─────────┘
```

## 核心设计决策

### 1. 真 Agent：Anthropic SDK 原生 tool use

**决策**：用 Anthropic SDK 的 `messages.create(tools=[...])` 让 LLM 自主决策调用哪个工具。

**为什么不是流水线**：legacy 项目是硬编码"搜索→抓取→LLM→报告"顺序，LLM 只被调用一次，没有自主性。真 Agent 应该 LLM 在循环里决定下一步做什么。

**实现**：
```python
# orchestrator.py 核心循环
while not done:
    response = client.messages.create(
        messages=messages,
        tools=registry.to_anthropic(),
        max_tokens=4096,
    )
    if response.stop_reason == "tool_use":
        for block in response.content:
            if block["type"] == "tool_use":
                result = execute_tool(block)
                tool_results.append(result)
        messages.append({"role": "user", "content": tool_results})
    else:
        done = True
```

**保护**：`max_iterations=20` 硬上限，防止循环失控烧钱。

### 2. 三层证据评分

**问题**：LLM 单独评分有 20-30% 误判率，首页和歧义命中会被误判为有效证据。

**决策**：分层评估，每层职责不同。

| Layer | 实现 | 成本 | 作用 |
|-------|------|------|------|
| Layer 1 | 规则（首页检测、黑名单、歧义识别） | 0 | 砍掉 60-70% 明显垃圾 |
| Layer 2 | Haiku LLM 粗筛 | $0.001/次 | 评分 0-10，≥7 进入抓取 |
| Layer 3 | Sonnet LLM 复评 | $0.01/次 | 只跑 4-6 分边界 case |

**黄金集测试**：30 个人工标注用例，CI 守门准确率 ≥ 85%。

### 3. 每个 tool_call 持久化

**决策**：orchestrator 每执行一个 tool_use block 就写一条 `tool_calls` 记录。

**为什么**：
- 调试：看 LLM 调了什么工具
- 审计：用户投诉时追溯
- 计费：按 token 收费
- 可视化：UI 渲染执行时间线

### 4. 断点续跑

**决策**：`agent_runs.messages` 存完整 Anthropic messages 历史（JSONB）。

**为什么**：长任务（5-10 分钟）可能被进程崩溃打断。重启后从 DB 读 messages，传 `resume_from=agent_run_id` 给 orchestrator 继续跑。

**坑**：SQLAlchemy 的 JSONB 不检测原地修改（`agent_run.messages.append(...)` 不会触发 UPDATE）。必须 `agent_run.messages = list(messages)` 创建新 list 才会持久化。

### 5. 单租户先行（不引入 tenant_id）

**决策**：Phase 3 不做多租户隔离，所有业务表用 `user_id` 隔离。

**为什么**：
- 中小企业 SaaS 先跑通业务比多租户复杂度重要
- 多租户需要中间件注入 tenant_id filter、跨租户测试矩阵——工程量翻倍
- 当前用户量小，单租户够用

**迁移路径**：未来加 `tenant_id` 只需一次 migration + 中间件改动，schema 干净。

### 6. 跨用户隔离：404 而非 403

**决策**：用户 A 访问用户 B 的 workflow，返回 404。

**为什么**：403 暴露资源存在性（攻击者知道 workflow_id 存在但不属于自己）。404 不暴露 existence，更安全。

### 7. Celery 每任务独立 engine

**决策**：Celery worker 里每个任务创建自己的 `create_async_engine + async_sessionmaker`。

**为什么**：asyncpg connection 绑定 event loop，Celery worker 的 prefork 模型每个子进程有独立 event loop。全局 engine 跨任务复用会报 "Future attached to a different loop"。

### 8. 不静默 fallback

**决策**：任何失败都明确报错，不悄悄返回预设数据。

**为什么**：legacy 项目最严重的问题是 LLM 失败时静默返回 fallback 数据，用户花 API 钱拿到假结果却不知情。本项目所有失败都：
- tool 失败：返回 `is_error: true` 给 LLM，让 LLM 决定重试或换工具
- LLM 失败：orchestrator 抛异常，workflow 标 failed + 写 error
- 搜索失败：返回空列表，不返回 fallback URL
- 抓取失败：返回 error，LLM 知道这个 URL 没用

### 9. 测试 fixture：dependency_overrides

**决策**：测试用 `fastapi_app.dependency_overrides[get_db]` 把 FastAPI 的 get_db 指向 test_engine 的 session_factory。

**为什么**：模块级 engine 绑定 FastAPI 启动时的 event loop，测试用 httpx.AsyncClient + ASGITransport 在另一个 event loop 跑，跨 loop asyncpg 报 'NoneType' object has no attribute 'send'。

## 数据模型

```
users              (id, email, password_hash, role, created_at)
workflows          (id, user_id FK, query, notes, status, error, created_at, completed_at)
agent_runs         (id, workflow_id FK, status, messages JSONB, final_output JSONB, started_at, ended_at)
tool_calls         (id, agent_run_id FK, tool_name, input_args JSONB, output_result JSONB, error, tokens, duration_ms)
evidence           (id, workflow_id FK, url, title, snippet, content, score, score_layer, fetched_at)
evidence_feedback  (id, user_id FK, evidence_id FK, useful, comment, created_at)
usage_records      (id, user_id FK, period_date, workflows_started, tool_calls, tokens, UNIQUE(user_id, period_date))
```

## LLM Provider

**火山引擎方舟 Claude 兼容协议**（底层 GLM-5.2）：

- 端点：`https://ark.cn-beijing.volces.com/api/coding`
- 用 Anthropic SDK 直连，tool use 格式完全兼容
- 配置：`.env` 里 `VOLC_API_KEY` / `VOLC_BASE_URL` / `VOLC_MODEL`

**为什么不是 Anthropic 官方**：用户在中国大陆，国际网络不稳定。火山引擎方舟提供 Claude 兼容协议，tool use 格式完全兼容（验证过：返回 `tool_use` block + `stop_reason="tool_use"`）。

**已知问题**：GLM-5.2 的 tool use 质量比 Claude 弱，calculate_roi 工具偶尔失败。orchestrator 靠 max_iterations=20 兜底自愈。

## 前端架构

```
React 18 + TypeScript + Vite
├── TanStack Query    # 数据请求 + 缓存
├── Zustand           # 客户端状态 (auth store)
├── React Router      # 路由
├── Tailwind CSS      # 样式
├── shadcn/ui         # 组件库 (基于 Radix UI)
└── sonner            # toast 通知
```

**实时进度**：用 TanStack Query 的 `refetchInterval` 轮询（2 秒），而非 WebSocket。理由：Agent 一步要 10-30 秒，轮询完全够用，实现简单可靠。WebSocket 延后到 V2。

## 性能考量

- **搜索缓存**：每次都打 ddgs，未来加 Redis 缓存（query hash → 结果，TTL 1h）
- **抓取并发**：score ≥ 7 的 URL 并发抓取（asyncio.gather 最多 5 并发）
- **LLM 降级**：Haiku 故障 → Sonnet 全量（成本↑5x）；Sonnet 故障 → Haiku + 标记低置信度
- **任务超时**：Celery task_time_limit=600s，soft_time_limit=540s

## 安全

- 密码：argon2-cffi（OWASP 推荐）
- JWT：HS256 + jti 声明（每个 token 唯一）+ access 15min / refresh 7day
- 防枚举：login 不区分用户不存在/密码错
- 跨用户：404 不暴露存在性
- CORS：白名单，不开放 `*`
- 配置：所有敏感信息走环境变量，不写代码里
