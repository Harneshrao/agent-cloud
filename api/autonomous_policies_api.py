"""
Autonomous workforce policies: control which agents may launch workflows,
max frequency, and resource limits.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import require_project_context
from database.autonomous_policies import (
    set_policy,
    list_policies_for_project,
    get_policy,
)

router = APIRouter(prefix="/autonomous", tags=["autonomous-policies"])


class SetPolicyBody(BaseModel):
    """Request body for POST /autonomous/policies."""

    agent_name: str = Field(..., description="Agent name or '*' for default for any agent")
    allowed: bool = Field(True, description="Whether this agent may launch workflows")
    max_launches_per_hour: int | None = Field(
        None,
        description="Max workflow launches per hour (rate limit)",
    )
    max_concurrent_workflows: int | None = Field(
        None,
        description="Max concurrent workflows (resource limit)",
    )


@router.get("/policies")
def list_policies(context: dict = Depends(require_project_context)):
    """List autonomous workforce policies for the project."""
    project_id = context["project_id"]
    policies = list_policies_for_project(project_id)
    return {"policies": policies, "project_id": project_id}


@router.post("/policies")
def post_set_policy(
    body: SetPolicyBody,
    context: dict = Depends(require_project_context),
):
    """Set or update policy for an agent (or '*' for default)."""
    project_id = context["project_id"]
    policy = set_policy(
        project_id=project_id,
        agent_name=body.agent_name,
        allowed=body.allowed,
        max_launches_per_hour=body.max_launches_per_hour,
        max_concurrent_workflows=body.max_concurrent_workflows,
    )
    return {"status": "ok", "policy": policy}


@router.get("/policies/{agent_name}")
def get_agent_policy(
    agent_name: str,
    context: dict = Depends(require_project_context),
):
    """Get policy for an agent. Returns default (allow, no limit) if not set."""
    project_id = context["project_id"]
    policy = get_policy(project_id, agent_name)
    if policy is None:
        return {"project_id": project_id, "agent_name": agent_name, "allowed": True, "max_launches_per_hour": None, "max_concurrent_workflows": None}
    return policy
