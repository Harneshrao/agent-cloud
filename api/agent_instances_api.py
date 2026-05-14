"""
Persistent agent identity API: create and manage long-lived AI agents.

POST /agent-instances - create instance (agent_name, project_id, role, state?)
GET /agent-instances - list instances for project
GET /agent-instances/{id} - get one instance
POST /agent-instances/{id}/run - enqueue a task for this instance (task assigned to instance)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.deps import require_project_context
from api.schemas.task_responses import (
    AgentInstanceAutonomousCycleResponse,
    AgentInstanceRunResponse,
)
from database.agent_instances import (
    create_instance,
    get_instance,
    list_instances_for_project,
    update_state,
)
from database.autonomous_policies import record_launch_and_check, LAUNCH_SOURCE_AGENT
from task_queue.task_queue import enqueue_task

router = APIRouter(prefix="/agent-instances", tags=["agent-instances"])


class CreateInstanceBody(BaseModel):
    agent_name: str = Field(..., description="Registered agent name (e.g. research_agent)")
    role: Optional[str] = Field(None, description="Human-readable role (e.g. AI Researcher)")
    state: Optional[Dict[str, Any]] = Field(None, description="Initial state (conversation context, variables)")
    instance_id: Optional[str] = Field(None, description="Custom id; if omitted, generated")


@router.post("")
def post_create_instance(
    body: CreateInstanceBody,
    context: dict = Depends(require_project_context),
):
    """
    Create a persistent agent instance (e.g. AI Researcher, AI Sales Assistant).
    Requires project context. Returns the created instance.
    """
    project_id = context["project_id"]
    inst = create_instance(
        agent_name=body.agent_name,
        project_id=project_id,
        role=body.role,
        state=body.state,
        instance_id=body.instance_id,
    )
    return inst


@router.get("")
def get_instances(
    agent_name: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    context: dict = Depends(require_project_context),
):
    """List agent instances for the project, optionally filtered by agent_name."""
    project_id = context["project_id"]
    items = list_instances_for_project(project_id, agent_name=agent_name, limit=limit)
    return {"instances": items, "count": len(items)}


@router.get("/{instance_id}")
def get_instance_by_id(
    instance_id: str,
    context: dict = Depends(require_project_context),
):
    """Get one agent instance. Returns 403 if instance belongs to another project."""
    inst = get_instance(instance_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Agent instance not found")
    if inst.get("project_id") != context["project_id"]:
        raise HTTPException(status_code=403, detail="Access denied to this instance")
    return inst


class RunTaskBody(BaseModel):
    task: str = Field(..., description="Task text (e.g. 'research competitor pricing')")


@router.post("/{instance_id}/run")
def post_instance_run(
    instance_id: str,
    body: RunTaskBody,
    context: dict = Depends(require_project_context),
):
    """
    Enqueue a task for this agent instance. The task will be executed by the
    instance's agent with instance-scoped memory and state.
    """
    inst = get_instance(instance_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Agent instance not found")
    if inst.get("project_id") != context["project_id"]:
        raise HTTPException(status_code=403, detail="Access denied to this instance")
    project_id = context["project_id"]
    task_id = enqueue_task(
        {"task": body.task, "agent_instance_id": instance_id, "agent": inst.get("agent_name")},
        project_id=project_id,
    )
    return {
        "status": "task queued",
        "task_id": task_id,
        "agent_instance_id": instance_id,
        "agent_name": inst.get("agent_name"),
        "task": body.task,
    }


@router.post("/{instance_id}/autonomous-cycle", response_model=AgentInstanceAutonomousCycleResponse)
def post_instance_autonomous_cycle(
    instance_id: str,
    context: dict = Depends(require_project_context),
):
    """
    Run the agent instance's autonomous cycle: call run_autonomous_cycle() and enqueue
    any returned task(s) subject to policy. Use for agents that initiate workflows (e.g.
    AI researcher detects market change and launches research workflow).
    """
    inst = get_instance(instance_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Agent instance not found")
    if inst.get("project_id") != context["project_id"]:
        raise HTTPException(status_code=403, detail="Access denied to this instance")
    project_id = context["project_id"]
    agent_name = inst.get("agent_name")
    if not record_launch_and_check(agent_name, project_id, LAUNCH_SOURCE_AGENT):
        raise HTTPException(
            status_code=429,
            detail="Autonomous launch not allowed by policy or rate limit exceeded",
        )
    try:
        from registry.agent_registry import agent_registry
        agent_instance = agent_registry.get_agent(agent_name)
    except Exception:
        agent_instance = None
    if agent_instance is None:
        raise HTTPException(status_code=400, detail=f"Agent '{agent_name}' not registered")
    agent_instance._memory_project_id = project_id
    agent_instance._memory_agent_instance_id = instance_id
    out = agent_instance.run_autonomous_cycle()
    task_ids = []
    if out is None:
        pass
    elif isinstance(out, dict):
        payload = dict(out)
        if "task" not in payload and "agent" not in payload:
            payload["task"] = str(payload.get("task", ""))
        payload["agent_instance_id"] = instance_id
        if "agent" not in payload:
            payload["agent"] = agent_name
        task_ids.append(enqueue_task(payload, project_id=project_id))
    elif isinstance(out, (list, tuple)):
        for item in out:
            if isinstance(item, dict):
                payload = dict(item)
                payload["agent_instance_id"] = instance_id
                if "agent" not in payload:
                    payload["agent"] = agent_name
                task_ids.append(enqueue_task(payload, project_id=project_id))
    return {
        "status": "ok",
        "agent_instance_id": instance_id,
        "tasks_queued": len(task_ids),
        "task_ids": task_ids,
    }


class StateBody(BaseModel):
    state: Dict[str, Any] = Field(..., description="State to set (conversation context, internal variables)")


@router.patch("/{instance_id}/state")
def patch_instance_state(
    instance_id: str,
    body: StateBody,
    context: dict = Depends(require_project_context),
):
    """Update the persisted state (conversation context, internal variables) for an instance."""
    inst = get_instance(instance_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Agent instance not found")
    if inst.get("project_id") != context["project_id"]:
        raise HTTPException(status_code=403, detail="Access denied to this instance")
    ok = update_state(instance_id, body.state)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update state")
    return get_instance(instance_id)
