from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, Optional

from agent_runtime.loader import get_agent_class
from agent_runtime.logging import RunLogger
from agent_runtime.memory import Memory
from agentcloud_sdk.agent import AgentContext
from database.db import db


def execute_agent_task(
    task_id: uuid.UUID,
    agent_name: str,
    inputs: Dict[str, Any],
    project_id: Optional[uuid.UUID] = None,
) -> Any:
    """
    Execute a filesystem-backed agent for the given task.

    This is a synchronous wrapper designed to be called from the worker loop.
    It runs the agent's async run() method in a local event loop and returns
    the result to the caller. Task status and result persistence are handled
    by the existing worker/orchestrator pipeline.
    """
    AgentCls = get_agent_class(agent_name)
    if AgentCls is None:
        raise RuntimeError(f"Unknown filesystem agent: {agent_name}")

    # Create an agent_runs row for observability; store initial status + inputs.
    run_id = db.store_agent_run(task_id=task_id, agent_name=agent_name, output={"status": "started", "inputs": inputs})

    logger = RunLogger(task_id=task_id, run_id=run_id, agent_name=agent_name)
    memory = Memory(agent_name=agent_name, task_id=task_id, project_id=project_id)
    ctx = AgentContext(
        run_id=run_id,
        task_id=task_id,
        agent_name=agent_name,
        logger=logger,
        memory=memory,
        tools=None,
        config={},
    )

    agent = AgentCls()

    async def _run() -> Any:
        return await agent.run(inputs, ctx)

    start = time.time()
    try:
        result = asyncio.run(_run())
        duration = time.time() - start
        logger.info("agent_run_completed", duration_seconds=duration)
        # Append a final agent_runs row capturing the completed output.
        db.store_agent_run(task_id=task_id, agent_name=agent_name, output={"status": "completed", "duration_seconds": duration, "output": result})
        return result
    except Exception as exc:  # pragma: no cover - safety net
        duration = time.time() - start
        logger.error("agent_run_failed", duration_seconds=duration, error=str(exc))
        db.store_agent_run(
            task_id=task_id,
            agent_name=agent_name,
            output={"status": "failed", "duration_seconds": duration, "error": str(exc)},
        )
        raise

