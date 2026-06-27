"""Backend Agent - 根据 PRD 生成后端代码."""
from __future__ import annotations

from typing import Any

from app.agent.projects.base_agent import AgentAction, AgentState, ProjectAgent
from app.agent.projects.utils import extract_code_block, llm_chat
from app.core.logging import get_logger

log = get_logger(__name__)


class BackendAgent(ProjectAgent):
    role = "backend"

    def __init__(self, project_id: int, context: dict[str, Any]):
        super().__init__(project_id, context)
        self.prd = context.get("prd", "")
        self.files: dict[str, str] = {}
        self.api_spec = ""

    async def perceive(self) -> AgentState:
        return AgentState(
            project_id=self.project_id,
            role=self.role,
            data={"prd": self.prd, "files": list(self.files.keys())},
        )

    async def reason(self, state: AgentState) -> AgentAction:
        if not self.files:
            return AgentAction(type="GENERATE_BACKEND", payload=state.data)
        return AgentAction(type="WAIT")

    async def act(self, action: AgentAction) -> None:
        if action.type == "GENERATE_BACKEND":
            log.info("backend_generating", project_id=self.project_id)
            await self._generate_api_spec()
            await self._generate_files()
            self.record_action("GENERATE_BACKEND")
            await self.save_memory(
                observation=f"生成后端文件: {list(self.files.keys())}",
                insight="Express + TypeScript + Prisma 是默认技术栈",
                importance=7,
            )
            self.mark_done()

    async def _generate_api_spec(self) -> None:
        prompt = f"""根据以下 PRD, 输出后端 API 设计:

{self.prd}

请输出:
1. 主要数据实体 (Entity) 和字段
2. RESTful API 端点列表 (METHOD /path)
3. 使用 Express + TypeScript + Prisma + SQLite

用 Markdown 输出。"""
        self.api_spec = await llm_chat(
            system="你是一位后端架构师。请输出简洁的 API 设计文档。",
            user=prompt,
            temperature=0.2,
            llm=self.llm,
        )

    async def _generate_files(self) -> None:
        # 为了稳定和可控, 使用模板 + LLM 生成关键文件
        package_json = """{
  "name": "generated-backend",
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "tsx src/index.ts",
    "build": "tsc",
    "start": "node dist/index.js",
    "db:push": "prisma db push"
  },
  "dependencies": {
    "@prisma/client": "^5.20.0",
    "cors": "^2.8.5",
    "express": "^4.21.0",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "@types/cors": "^2.8.17",
    "@types/express": "^4.17.21",
    "@types/node": "^22.7.0",
    "prisma": "^5.20.0",
    "tsx": "^4.19.0",
    "typescript": "^5.6.0"
  }
}
"""
        tsconfig_json = """{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src/**/*"]
}
"""
        prisma_schema = await self._generate_prisma_schema()
        index_ts = await self._generate_index_ts()
        routes_ts = await self._generate_routes_ts()

        self.files["backend/package.json"] = package_json
        self.files["backend/tsconfig.json"] = tsconfig_json
        self.files["backend/prisma/schema.prisma"] = prisma_schema
        self.files["backend/src/index.ts"] = index_ts
        self.files["backend/src/routes.ts"] = routes_ts
        self.files["backend/README.md"] = "# Generated Backend\n\nRun `npm install && npm run dev`"

    async def _generate_prisma_schema(self) -> str:
        prompt = f"""根据以下 PRD, 生成 Prisma schema。

{self.prd}

要求:
- 使用 SQLite provider
- 包含至少 2 个 model
- 每个 model 有 id, createdAt, updatedAt
- 只输出 schema 内容, 不包含 ``` 标记

示例格式:
generator client {{
  provider = "prisma-client-js"
}}

datasource db {{
  provider = "sqlite"
  url      = env("DATABASE_URL")
}}

model Todo {{
  id        String   @id @default(cuid())
  title     String
  completed Boolean  @default(false)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}}"""
        return await llm_chat(
            system="你是一位数据库专家。只输出 Prisma schema 代码, 不解释。",
            user=prompt,
            temperature=0.2,
            llm=self.llm,
        )

    async def _generate_index_ts(self) -> str:
        return """import express from 'express';
import cors from 'cors';
import routes from './routes.js';

const app = express();
app.use(cors());
app.use(express.json());
app.use('/api/v1', routes);

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
"""

    async def _generate_routes_ts(self) -> str:
        prompt = f"""根据以下 PRD 和 API 设计, 生成 Express 路由代码 (TypeScript ESM)。

PRD:
{self.prd}

API Spec:
{self.api_spec}

要求:
- 使用 import/export (ESM)
- 使用 zod 做简单输入校验
- 使用内存数组做数据存储 (不连接真实 DB, 便于 demo)
- 只输出 routes.ts 内容, 不包含 ``` 标记

示例:
import {{ Router }} from 'express';
import {{ z }} from 'zod';

const router = Router();
const todos: any[] = [];

const createSchema = z.object({{ title: z.string() }});

router.get('/todos', (req, res) => res.json({{ data: todos }}));
router.post('/todos', (req, res) => {{
  const data = createSchema.parse(req.body);
  const todo = {{ id: String(todos.length + 1), title: data.title, completed: false }};
  todos.push(todo);
  res.json({{ data: todo }});
}});

export default router;"""
        code = await llm_chat(
            system="你是一位后端工程师。只输出 TypeScript 代码, 不解释。",
            user=prompt,
            temperature=0.2,
            llm=self.llm,
        )
        return extract_code_block(code, "typescript")

    def get_files(self) -> dict[str, str]:
        return self.files

    def get_api_spec(self) -> str:
        return self.api_spec
