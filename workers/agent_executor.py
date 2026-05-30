"""
Canonical agent execution body for the production worker loop.

Invoked by ``workers.guaranteed_loop`` via EXECUTOR_MODULE=workers.agent_executor.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Tuple

from agent_runtime.execution_engine import execute_agent_task
from database.db import db
from database.workflow_checkpoints import set_running as checkpoint_set_running
from engine.dag_scheduler import on_node_completed
from engine.safe_execution import (
    AgentTimeoutError,
    MemoryLimitExceededError,
    run_with_timeout,
)
from orchestrator.orchestrator import run_pipeline, run_single_agent_node

# Re-export for task_outcome / guaranteed_loop
ExecutionSecurityError = (AgentTimeoutError, MemoryLimitExceededError)


def _resolve_agent_instance(agent_instance_id: Any) -> Tuple[str | None, dict]:
    try:
        from database.agent_instances import get_instance

        inst = get_instance(agent_instance_id)
        if inst is None:
            return None, {}
        return inst.get("agent_name"), inst.get("state") or {}
    except Exception:
        return None, {}


def run(task: Dict[str, Any]) -> Any:
    """
    Execute one claimed task dict. Raises on failure (retry/DLQ handled by loop).
    """
    workflow_id = task.get("workflow_id")
    node_id = task.get("node_id")
    idempotency_key = task.get("idempotency_key")
    if idempotency_key is None:
        if workflow_id is not None and node_id is not None:
            idempotency_key = f"{workflow_id}:{node_id}"
        else:
            idempotency_key = str(task["id"])

    agent_instance_id = task.get("agent_instance_id")
    instance_state: dict = {}
    agent_name = task.get("agent")
    if agent_instance_id:
        resolved_name, instance_state = _resolve_agent_instance(agent_instance_id)
        if resolved_name and not agent_name:
            agent_name = resolved_name
    if task.get("input") is not None:
        instance_state["input"] = task["input"]
    if agent_name is None:
        agent_name = ""

    deployment_id = task.get("deployment_id")
    if deployment_id is not None:
        import os
        from agent_runtime.deployment_runtime import execute_deployment_task

        project_id = db.get_task_project_id(task["id"])
        timeout = int(os.environ.get("AGENT_TIMEOUT_SECONDS", "60"))
        return run_with_timeout(
            lambda: execute_deployment_task(
                uuid.UUID(str(task["id"])),
                uuid.UUID(str(deployment_id)),
                task.get("input") or instance_state.get("input") or {},
                project_id=uuid.UUID(str(project_id)) if project_id else None,
            ),
            timeout_seconds=timeout + 15,
            task_id=uuid.UUID(str(task["id"])),
            agent_name=task.get("agent"),
        )

    if workflow_id is not None and node_id is not None:
        return _run_dag_node(
            task,
            agent_name,
            agent_instance_id,
            instance_state,
        )

    return _run_single_task(
        task,
        agent_name,
        agent_instance_id,
        instance_state,
    )


def _run_dag_node(
    task: Dict[str, Any],
    agent_name: str,
    agent_instance_id: Any,
    instance_state: dict,
    idempotency_key: str,
) -> Any:
    wf_uuid = uuid.UUID(str(task["workflow_id"]))
    task_uuid = uuid.UUID(str(task["id"]))
    checkpoint_set_running(wf_uuid, task["node_id"])
    out = run_with_timeout(
        lambda: run_single_agent_node(
            task_uuid,
            task["task"],
            agent_name,
            agent_instance_id=agent_instance_id,
            instance_state=instance_state,
        ),
        timeout_seconds=60,
        task_id=task_uuid,
        agent_name=agent_name,
    )
    if isinstance(out, tuple):
        result, state_snapshot = out
        if agent_instance_id and state_snapshot is not None:
            try:
                from database.agent_instances import update_state

                update_state(agent_instance_id, state_snapshot)
            except Exception:
                pass
    else:
        result = out
    on_node_completed(wf_uuid, task["node_id"], task_uuid, agent_name, result)
    _update_installation_output(task, task_uuid, result)
    return result


def _run_single_task(
    task: Dict[str, Any],
    agent_name: str,
    agent_instance_id: Any,
    instance_state: dict,
) -> Any:
    task_uuid = uuid.UUID(str(task["id"]))
    if task.get("runtime") == "v2":
        project_id = db.get_task_project_id(task["id"])
        inputs = task.get("input") or {}
        result = run_with_timeout(
            lambda: execute_agent_task(
                task_id=task["id"],
                agent_name=agent_name or task.get("agent") or "",
                inputs=inputs,
                project_id=project_id,
            ),
            timeout_seconds=60,
            task_id=task["id"],
            agent_name=agent_name or task.get("agent"),
        )
    else:
        out = run_with_timeout(
            lambda: run_pipeline(
                task["task"],
                task_id=task["id"],
                agent=agent_name or task.get("agent"),
                agent_instance_id=agent_instance_id,
                instance_state=instance_state,
            ),
            timeout_seconds=60,
            task_id=task["id"],
            agent_name=agent_name or task.get("agent"),
        )
        if isinstance(out, tuple):
            result, state_snapshot = out
            if agent_instance_id and state_snapshot is not None:
                try:
                    from database.agent_instances import update_state

                    update_state(agent_instance_id, state_snapshot)
                except Exception:
                    pass
        else:
            result = out

    _update_installation_output(task, task_uuid, result)
    return result


def _update_installation_output(
    task: Dict[str, Any], task_uuid: uuid.UUID, result: Any
) -> None:
    if task.get("installation_id") is None:
        return
    try:
        from database.agent_run_results import update_output

        update_output(task_uuid, result)
    except Exception:
        pass
