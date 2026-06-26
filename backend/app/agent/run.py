"""CLI entry point - run agent from command line.

用法:
    uv run python -m app.agent.run "招聘筛选流程"
    uv run python -m app.agent.run "招聘筛选流程" --resume-from 5
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from app.agent.orchestrator import Orchestrator
from app.core.logging import setup_logging
from app.db.session import async_session_factory


async def main(query: str, resume_from: int | None = None) -> int:
    setup_logging()
    orch = Orchestrator(async_session_factory)
    agent_run = await orch.run(query, workflow_id=f"cli-{query[:20]}", resume_from=resume_from)
    print(f"\n=== Agent Run Complete ===", file=sys.stderr)
    print(f"ID: {agent_run.id}", file=sys.stderr)
    print(f"Status: {agent_run.status}", file=sys.stderr)
    print(f"Iterations: {agent_run.current_iteration}", file=sys.stderr)
    if agent_run.error:
        print(f"Error: {agent_run.error}", file=sys.stderr)
    if agent_run.final_output:
        import json
        print(json.dumps(agent_run.final_output, ensure_ascii=False, indent=2))
    return 0 if agent_run.status == "completed" else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Workflow Discovery Agent")
    parser.add_argument("query", help="Workflow query, e.g. '招聘筛选流程'")
    parser.add_argument("--resume-from", type=int, default=None, help="Resume from agent_run_id")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    exit_code = asyncio.run(main(args.query, args.resume_from))
    sys.exit(exit_code)
