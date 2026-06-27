"""Frontend Agent - 根据 PRD 和后端 API 设计生成前端代码."""
from __future__ import annotations

from typing import Any

from app.agent.projects.base_agent import AgentAction, AgentState, ProjectAgent
from app.agent.projects.utils import extract_code_block, llm_chat
from app.core.logging import get_logger

log = get_logger(__name__)


class FrontendAgent(ProjectAgent):
    role = "frontend"

    def __init__(self, project_id: int, context: dict[str, Any]):
        super().__init__(project_id, context)
        self.prd = context.get("prd", "")
        self.api_spec = context.get("api_spec", "")
        self.files: dict[str, str] = {}

    async def perceive(self) -> AgentState:
        return AgentState(
            project_id=self.project_id,
            role=self.role,
            data={"prd": self.prd, "api_spec": self.api_spec, "files": list(self.files.keys())},
        )

    async def reason(self, state: AgentState) -> AgentAction:
        if not self.files:
            return AgentAction(type="GENERATE_FRONTEND", payload=state.data)
        return AgentAction(type="WAIT")

    async def act(self, action: AgentAction) -> None:
        if action.type == "GENERATE_FRONTEND":
            log.info("frontend_generating", project_id=self.project_id)
            await self._generate_files()
            self.record_action("GENERATE_FRONTEND")
            await self.save_memory(
                observation=f"生成前端文件: {list(self.files.keys())}",
                insight="Next.js + Tailwind CSS 是默认技术栈",
                importance=7,
            )
            self.mark_done()

    async def _generate_files(self) -> None:
        package_json = """{
  "name": "generated-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start"
  },
  "dependencies": {
    "next": "14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.6.0"
  }
}
"""
        tsconfig_json = """{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
"""
        next_config = """/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
"""
        postcss_config = """module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
"""
        tailwind_config = """/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
"""
        global_css = """@tailwind base;
@tailwind components;
@tailwind utilities;
"""
        app_layout = await self._generate_layout_tsx()
        app_page = await self._generate_page_tsx()

        self.files["frontend/package.json"] = package_json
        self.files["frontend/tsconfig.json"] = tsconfig_json
        self.files["frontend/next.config.mjs"] = next_config
        self.files["frontend/postcss.config.js"] = postcss_config
        self.files["frontend/tailwind.config.js"] = tailwind_config
        self.files["frontend/src/app/globals.css"] = global_css
        self.files["frontend/src/app/layout.tsx"] = app_layout
        self.files["frontend/src/app/page.tsx"] = app_page
        self.files["frontend/README.md"] = "# Generated Frontend\n\nRun `npm install && npm run dev`"

    async def _generate_layout_tsx(self) -> str:
        return """export const metadata = {
  title: 'Generated App',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
"""

    async def _generate_page_tsx(self) -> str:
        prompt = f"""根据以下 PRD 和后端 API 设计, 生成一个 Next.js 14 App Router 页面 (page.tsx)。

PRD:
{self.prd}

后端 API:
{self.api_spec}

要求:
- 使用 React Server Component + Client Component 混合
- 使用 Tailwind CSS 做样式
- 页面需要包含: 列表展示、创建表单、删除/完成操作
- API base URL 从环境变量读取, 默认 http://localhost:3001
- 只输出 page.tsx 内容, 不包含 ``` 标记

示例结构:
'use client';
import {{ useEffect, useState }} from 'react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api/v1';

export default function Home() {{
  const [items, setItems] = useState([]);
  ...
}}"""
        code = await llm_chat(
            system="你是一位前端工程师。只输出 TypeScript/React 代码, 不解释。",
            user=prompt,
            temperature=0.3,
            llm=self.llm,
        )
        return extract_code_block(code, "tsx")

    def get_files(self) -> dict[str, str]:
        return self.files
