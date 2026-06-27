"""CLI entry point - run agent from command line.

用法:
    uv run python -m app.agent.run "招聘筛选流程" --user-id 1
    uv run python -m app.agent.run "招聘筛选流程" --user-id 1 --resume-from 5
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

from app.agent.orchestrator import Orchestrator
from app.core.logging import setup_logging
from app.db.session import async_session_factory
from app.models import Workflow


async def main(query: str, user_id: int, resume_from: int | None = None) -> int:
    setup_logging()
    async with async_session_factory() as session:
        if resume_from is not None:
            # 恢复模式: 不新建 workflow, 直接传 workflow_id (从 agent_run 反查)
            from app.models import AgentRun
            agent_run = await session.get(AgentRun, resume_from)
            if agent_run is None:
                print(f"agent_run not found: {resume_from}", file=sys.stderr)
                return 1
            workflow_id = agent_run.workflow_id
        else:
            # 新建 workflow
            wf = Workflow(user_id=user_id, query=query, status="running")
            session.add(wf)
            await session.commit()
            await session.refresh(wf)
            workflow_id = wf.id

        orch = Orchestrator(async_session_factory)
        agent_run = await orch.run(query, workflow_id=workflow_id, resume_from=resume_from)

        # 同步 workflow 状态
        wf = await session.get(Workflow, workflow_id)
        if wf is not None:
            wf.status = agent_run.status
            from datetime import datetime
            if agent_run.status in ("completed", "failed"):
                wf.completed_at = datetime.utcnow()
                if agent_run.error:
                    wf.error = agent_run.error
            await session.commit()

    print(f"\n=== Agent Run Complete ===", file=sys.stderr)
    print(f"ID: {agent_run.id}", file=sys.stderr)
    print(f"Workflow ID: {workflow_id}", file=sys.stderr)
    print(f"Status: {agent_run.status}", file=sys.stderr)
    print(f"Iterations: {agent_run.current_iteration}", file=sys.stderr)
    if agent_run.error:
        print(f"Error: {agent_run.error}", file=sys.stderr)
    if agent_run.final_output:
        print(json.dumps(agent_run.final_output, ensure_ascii=False, indent=2))
    return 0 if agent_run.status == "completed" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Workflow Discovery Agent")
    parser.add_argument("query", help="Workflow query, e.g. '招聘筛选流程'")
    parser.add_argument("--user-id", type=int, required=True, help="Owner user id")
    parser.add_argument("--resume-from", type=int, default=None, help="Resume from agent_run_id")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    exit_code = asyncio.run(main(args.query, args.user_id, args.resume_from))
    sys.exit(exit_code)
