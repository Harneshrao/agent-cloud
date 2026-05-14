"""
Agent Marketplace API: publish, discover, and run agents.

Endpoints:
  POST /agents/publish       - Register a new agent version in the marketplace.
  GET  /agents/store        - List all published agents.
  GET  /agents/{name}/latest - Return the latest version of the named agent.
  POST  /agents/run         - Run a published or built-in agent (requires project context, enqueues task).
  POST  /agent/run          - Same as POST /agents/run (SDK / legacy path).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.auth_api import get_current_user_optional
from api.deps import require_project_context
from api.schemas.task_responses import MarketplaceAgentRunResponse
from agents.loader import load_agents
from database.agent_installs import record_install
from database.agent_store import get_agent_by_name, list_published_agents, publish_agent
from registry.agent_registry import agent_registry
from database.agent_pricing import set_agent_developer
from engine.quota_checker import check_quota
from task_queue.task_queue import enqueue_task


router = APIRouter(prefix="/agents", tags=["marketplace"])
# Back-compat alias for SDKs and docs that use singular /agent/run
agent_run_alias_router = APIRouter(tags=["marketplace"])


class PublishAgentRequest(BaseModel):
    """Request body for POST /agents/publish."""

    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    version: str = Field(..., description="Semantic version, e.g. 1.0.0 or v1")
    capabilities: list = Field(..., description="List of capability keywords")
    author: str = Field(..., description="Author or organization")
    price: float = Field(0.0, ge=0, description="Price (e.g. 0 for free)")


class RunAgentRequest(BaseModel):
    """Request body for POST /agents/run."""

    agent: str = Field(..., description="Published agent name (e.g. research_agent)")
    task: str = Field(..., description="Task to run (e.g. research AI startup market)")
    region: str | None = Field(None, description="Target region for routing (e.g. us, eu, asia)")


@router.post("/publish")
def agents_publish(
    data: PublishAgentRequest,
    user: dict | None = Depends(get_current_user_optional),
):
    """
    Register a new agent version in the marketplace.
    (name, version) must be unique; publishing the same name+version again returns 409.
    If authenticated, the publishing user is set as the agent developer for revenue sharing.
    """
    try:
        agent = publish_agent(
            name=data.name,
            description=data.description,
            version=data.version,
            capabilities=data.capabilities,
            author=data.author,
            price=data.price,
        )
        if user is not None:
            try:
                set_agent_developer(data.name, user["id"])
            except Exception:
                pass
        return {"status": "published", "agent": agent}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/store")
def agents_store():
    """
    Return all published agents in the marketplace for discovery.
    """
    try:
        agents = list_published_agents()
        return {"agents": agents}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}/latest")
def agents_latest(name: str):
    """
    Return the latest version of the agent with the given name (by created_at).
    """
    try:
        agent = get_agent_by_name(name)
        if agent is None:
            raise HTTPException(status_code=404, detail=f"Agent '{name}' not found")
        from database.agent_pricing import get_price as get_agent_pricing
        pricing = get_agent_pricing(name)
        payload = {
            "name": agent["name"],
            "version": agent["version"],
            "description": agent["description"],
            "capabilities": agent["capabilities"],
        }
        if pricing:
            payload["price_per_run"] = pricing["price_per_run"]
            payload["currency"] = pricing["currency"]
        return payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _resolve_executable_agent_name(requested: str) -> str:
    """
    Prefer a published marketplace name; otherwise allow built-in registry agents.
    Accepts shorthand 'planner' -> 'planner_agent' when the latter is registered.
    """
    if get_agent_by_name(requested) is not None:
        return requested
    load_agents()
    if agent_registry.get_agent(requested) is not None:
        return requested
    if requested == "planner" and agent_registry.get_agent("planner_agent") is not None:
        return "planner_agent"
    raise HTTPException(
        status_code=404,
        detail=f"Agent '{requested}' not found in the marketplace or built-in registry",
    )


def _enqueue_agent_run(
    data: RunAgentRequest,
    context: dict,
) -> MarketplaceAgentRunResponse:
    """Shared body for POST /agents/run and POST /agent/run."""
    agent_name = _resolve_executable_agent_name(data.agent)
    project_id = context["project_id"]
    check_quota(project_id)
    record_install(agent_name, project_id)
    task_id = enqueue_task(
        {"task": data.task, "agent": agent_name},
        project_id=project_id,
        user_region=data.region,
    )
    return MarketplaceAgentRunResponse(
        status="task queued",
        agent=agent_name,
        task_id=task_id,
        project_id=project_id,
    )


@router.post("/run", response_model=MarketplaceAgentRunResponse)
def agents_run(
    data: RunAgentRequest,
    context: dict = Depends(require_project_context),
):
    """
    Run a published agent: validate the agent exists, then enqueue the task for the project.
    Requires Authorization and X-Project-ID (or project_id query).
    """
    try:
        return _enqueue_agent_run(data, context)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@agent_run_alias_router.post("/agent/run", response_model=MarketplaceAgentRunResponse)
def agent_run_alias(
    data: RunAgentRequest,
    context: dict = Depends(require_project_context),
):
    """Same as POST /agents/run (SDK / legacy path)."""
    try:
        return _enqueue_agent_run(data, context)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
