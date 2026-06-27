# API 文档

Base URL: `http://localhost:8001/api/v1`

Swagger UI: `http://localhost:8001/docs`（DEBUG=true 时可用）

## 认证

所有需要认证的端点都要 Bearer token：

```
Authorization: Bearer <access_token>
```

access token 15 分钟过期，用 refresh token 换新的。

---

## Auth 端点

### POST /auth/register

注册新用户。首个用户自动成为 admin，其余为 member。

```json
// Request
{
  "email": "user@example.com",
  "password": "Passw0rd!"
}

// Response 201
{
  "user": { "id": 1, "email": "user@example.com", "role": "admin" },
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

错误：
- 409 邮箱已注册
- 422 密码 < 8 位 / 邮箱格式错

### POST /auth/login

OAuth2 password flow，支持 Swagger Authorize 按钮。

```
// Request (application/x-www-form-urlencoded)
username=user@example.com&password=Passw0rd!

// Response 200
{
  "user": { ... },
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

错误：
- 401 用户不存在或密码错（不区分，防枚举）

### GET /auth/me

获取当前登录用户。

```json
// Response 200
{ "id": 1, "email": "user@example.com", "role": "admin" }
```

### POST /auth/refresh

用 refresh token 换新的 access + refresh token。

```json
// Request
{ "refresh_token": "eyJ..." }

// Response 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

错误：
- 401 token 无效 / 不是 refresh token / 已过期

---

## Workflow 端点

### POST /workflows

创建工作流并入队 Celery agent task。

```json
// Request
{ "query": "招聘筛选流程", "notes": "目标互联网行业" }

// Response 201
{ "workflow_id": 1, "status": "pending", "task_id": "celery-task-uuid" }
```

### GET /workflows

分页列出当前用户的工作流。

```
GET /workflows?page=1&page_size=20&status=running
```

```json
// Response 200
{
  "items": [
    {
      "id": 1,
      "user_id": 1,
      "query": "招聘筛选流程",
      "notes": "...",
      "status": "completed",
      "error": null,
      "created_at": "2026-06-26T10:00:00",
      "updated_at": "2026-06-26T10:05:00",
      "completed_at": "2026-06-26T10:05:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### GET /workflows/{id}

获取单个工作流详情。跨用户访问返回 404（不暴露存在性）。

### DELETE /workflows/{id}

删除工作流，级联删除 agent_runs / tool_calls / evidence。返回 204。

### GET /workflows/{id}/runs

列出 workflow 的 agent 执行记录。一个 workflow 可重跑多次。

```json
// Response 200
[
  {
    "id": 1,
    "status": "completed",
    "current_iteration": 4,
    "started_at": "2026-06-26T10:00:00",
    "ended_at": "2026-06-26T10:05:00",
    "error": null,
    "final_output": { "steps": [...], "pain_points": [...] }
  }
]
```

### GET /workflows/{id}/evidence

列出 workflow 的证据链，按 score 降序。

```json
// Response 200
[
  {
    "id": 1,
    "url": "https://example.com/article",
    "title": "招聘筛选流程七步骤",
    "snippet": "...",
    "score": 8.5,
    "score_reason": "真实流程文章，含详细步骤",
    "is_homepage": false,
    "is_disambiguation": false,
    "score_layer": 2,
    "word_count": 3200,
    "fetched_at": "2026-06-26T10:01:00"
  }
]
```

### GET /workflows/{id}/runs/{run_id}/tool_calls

列出某次 agent run 的 tool 调用序列（按时间顺序）。

```json
// Response 200
[
  {
    "id": 1,
    "tool_name": "search_web",
    "iteration": 0,
    "input_args": { "query": "招聘筛选流程" },
    "output_result": { "results": [...] },
    "error": null,
    "input_tokens": 100,
    "output_tokens": 50,
    "duration_ms": 5000,
    "created_at": "2026-06-26T10:00:01"
  }
]
```

---

## Usage 端点

### GET /usage/today

当前用户今日用量。

```json
// Response 200
{
  "user_id": 1,
  "period_start": "2026-06-26",
  "period_end": "2026-06-26",
  "workflows_started": 3,
  "workflows_completed": 2,
  "workflows_failed": 1,
  "tool_calls": 45,
  "input_tokens": 12500,
  "output_tokens": 8300,
  "search_queries": 5,
  "evidence_fetched": 8
}
```

### GET /usage/month

当前用户本月用量。格式同 today。

---

## Feedback 端点

### POST /feedback

提交证据反馈（有用/无用）。

```json
// Request
{
  "evidence_id": 1,
  "useful": true,
  "comment": "很有帮助"
}
```

### GET /feedback/stats?evidence_id=1

获取证据反馈统计。

```json
// Response 200
{ "useful_count": 5, "not_useful_count": 1 }
```

---

## Health & Root

### GET /health

```json
{ "status": "ok", "version": "0.1.0", "app": "Workflow Discovery Agent" }
```

### GET /

```json
{ "name": "Workflow Discovery Agent", "version": "0.1.0", "docs": "/docs" }
```

---

## 状态码

| 码 | 含义 |
|----|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功（无返回体） |
| 401 | 未认证 / token 无效 |
| 403 | 无权限（角色不足） |
| 404 | 资源不存在或不属于当前用户 |
| 409 | 冲突（如邮箱已注册） |
| 422 | 请求体校验失败 |
| 500 | 服务器错误 |

## 工具列表（Agent 可调用）

| Tool | 作用 |
|------|------|
| `search_web` | 调用 DuckDuckGo 搜索 |
| `score_evidence` | LLM 评估 URL 相关度（0-10） |
| `fetch_page` | Playwright 抓取页面正文 |
| `extract_workflow` | LLM 提取结构化工作流 |
| `identify_pain_points` | LLM 识别流程痛点 |
| `design_agent_flow` | LLM 设计 Agent 介入点 |
| `calculate_roi` | LLM 计算 ROI |
| `save_report` | 保存最终报告 |
