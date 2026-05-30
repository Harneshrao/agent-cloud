from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import require_project_can_run
from api.schemas.task_responses import AgentsV2RunResponse
from agent_runtime.loader import get_agent_class
from services.task_service import enqueue_task


router = APIRouter(prefix="/agents/v2", tags=["agents-v2"])


class RunV2AgentRequest(BaseModel):
    agent_name: str = Field(..., description="Filesystem agent name (AgentBase.name)")
    input: Dict[str, Any] = Field(default_factory=dict, description="Structured input payload for the agent")
    task_text: str = Field("Run v2 agent", description="Human-readable task description")


@router.post("/run", response_model=AgentsV2RunResponse)
def run_v2_agent(
    data: RunV2AgentRequest,
    context: Dict[str, Any] = Depends(require_project_can_run),
) -> AgentsV2RunResponse:
    """
    Enqueue a task for a v2 filesystem agent (agents/*/agent.py).

    Verifies the agent is discoverable via agent_runtime.loader and marks the
    task payload with runtime='v2' so the worker routes it through the new
    execution engine.
    """
    project_id = context["project_id"]
    if get_agent_class(data.agent_name) is None:
        raise HTTPException(status_code=400, detail=f"Unknown v2 agent: {data.agent_name}")

    payload = {
        "task": data.task_text,
        "agent": data.agent_name,
        "runtime": "v2",
        "input": data.input,
    }
    task_id = enqueue_task(payload, project_id=project_id)
    return AgentsV2RunResponse(
        status="task queued",
        task_id=task_id,
        agent=data.agent_name,
        task=data.task_text,
    )

