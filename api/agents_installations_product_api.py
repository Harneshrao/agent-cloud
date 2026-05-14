"""
Product Layer: Agent installations under /agents/installations.

User journey: Marketplace → Install Agent → Configure Inputs → Run Agent → View Result.
All routes are project-scoped. No infrastructure (workers, queues, DAG, regions) is exposed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import require_project_context
from api.schemas.task_responses import ProductInstallationRunResponse
from database.agent_installations import (
    install_agent,
    get_installation,
    list_installations_by_project,
    update_agent_configuration,
    validate_configuration,
    get_agent_input_schema,
)
from database.agent_run_results import list_runs_by_installation
from database.agent_schedules import (
    create_schedule,
    list_schedules_by_installation,
    get_schedule,
    update_schedule_status,
)
from database.agent_pricing import get_price as get_agent_price
from engine.quota_checker import check_quota
from task_queue.task_queue import enqueue_task


router = APIRouter(prefix="/agents/installations", tags=["agents-installations"])


class InstallAgentRequest(BaseModel):
    agent_name: str = Field(..., description="Agent name from marketplace")


class ConfigurationBody(BaseModel):
    """Configuration only (for PATCH /configuration)."""
    configuration: dict = Field(..., description="Key-value config matching agent input_schema")


class CreateScheduleRequest(BaseModel):
    cron_expression: str = Field(..., description="e.g. '0 9 * * *' daily 9am, '0 * * * *' hourly")
    status: str = Field("active", description="active | paused")


class UpdateScheduleRequest(BaseModel):
    status: str = Field(..., description="active | paused")


def _installation_for_project(installation_id: int, project_id: int):
    inst = get_installation(installation_id)
    if inst is None:
        raise HTTPException(status_code=404, detail="Installation not found")
    if inst["project_id"] != project_id:
        raise HTTPException(status_code=403, detail="Installation belongs to another project")
    return inst


# --- Install ---
@router.post("")
def install(
    data: InstallAgentRequest,
    context: dict = Depends(require_project_context),
):
    """Install an agent into the workspace. Validates agent exists and sets default configuration."""
    project_id = context["project_id"]
    try:
        installation = install_agent(project_id, data.agent_name)
        return {"installation": installation, "message": "Agent installed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_installations(context: dict = Depends(require_project_context)):
    """List installed agents in the workspace."""
    project_id = context["project_id"]
    return {"installations": list_installations_by_project(project_id)}


@router.get("/{installation_id}")
def get_installation_detail(
    installation_id: int,
    context: dict = Depends(require_project_context),
):
    """Get one installation with input_schema for rendering configuration forms."""
    project_id = context["project_id"]
    inst = _installation_for_project(installation_id, project_id)
    schema = get_agent_input_schema(inst["agent_name"])
    pricing = get_agent_price(inst["agent_name"])
    return {
        **inst,
        "input_schema": schema,
        "price_per_run": pricing.get("price_per_run") if pricing else None,
        "currency": pricing.get("currency") if pricing else "USD",
    }


# --- Configuration (forms from input_schema) ---
@router.patch("/{installation_id}/configuration")
def update_configuration(
    installation_id: int,
    data: ConfigurationBody,
    context: dict = Depends(require_project_context),
):
    """Update agent configuration. Validates against input_schema; required params must be present. UI can render forms from input_schema."""
    project_id = context["project_id"]
    inst = _installation_for_project(installation_id, project_id)
    valid, err = validate_configuration(inst["agent_name"], data.configuration)
    if not valid:
        raise HTTPException(status_code=400, detail=err or "Invalid configuration")
    update_agent_configuration(installation_id, data.configuration)
    return {"installation": get_installation(installation_id), "message": "Configuration saved"}


# --- One-click run ---
@router.post("/{installation_id}/run", response_model=ProductInstallationRunResponse)
def run_agent(
    installation_id: int,
    context: dict = Depends(require_project_context),
):
    """Run the agent now. Loads configuration, enqueues task. Returns task_id; result appears in run history when complete."""
    project_id = context["project_id"]
    check_quota(project_id)
    inst = _installation_for_project(installation_id, project_id)
    config = inst.get("configuration") or {}
    payload = {
        "agent": inst["agent_name"],
        "task": "Run with configured inputs",
        "input": config,
        "installation_id": installation_id,
    }
    task_id = enqueue_task(payload, project_id=project_id)
    return {
        "message": "Agent run started",
        "task_id": task_id,
        "installation_id": installation_id,
        "agent_name": inst["agent_name"],
    }


# --- Run history ---
@router.get("/{installation_id}/runs")
def list_runs(
    installation_id: int,
    limit: int = 50,
    offset: int = 0,
    context: dict = Depends(require_project_context),
):
    """Run history for this installation (run_id, task_id, status, output, execution_time, created_at)."""
    project_id = context["project_id"]
    _installation_for_project(installation_id, project_id)
    return {"runs": list_runs_by_installation(installation_id, limit=limit, offset=offset)}


# --- Schedules (hourly, daily, weekly) ---
@router.post("/{installation_id}/schedules")
def create_schedule_for_installation(
    installation_id: int,
    data: CreateScheduleRequest,
    context: dict = Depends(require_project_context),
):
    """Create a schedule. cron_expression examples: hourly '0 * * * *', daily '0 9 * * *', weekly '0 9 * * 0'."""
    project_id = context["project_id"]
    _installation_for_project(installation_id, project_id)
    schedule_id = create_schedule(installation_id, data.cron_expression, data.status)
    return {"schedule": get_schedule(schedule_id), "message": "Schedule created"}


@router.get("/{installation_id}/schedules")
def list_schedules_for_installation(
    installation_id: int,
    context: dict = Depends(require_project_context),
):
    """List schedules for this installation."""
    project_id = context["project_id"]
    _installation_for_project(installation_id, project_id)
    return {"schedules": list_schedules_by_installation(installation_id)}


# Schedule status update (by schedule_id) — keep under same product namespace
@router.patch("/schedules/{schedule_id}")
def update_schedule(
    schedule_id: int,
    data: UpdateScheduleRequest,
    context: dict = Depends(require_project_context),
):
    """Enable or pause a schedule."""
    s = get_schedule(schedule_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    inst = get_installation(s["installation_id"])
    if inst is None or inst["project_id"] != context["project_id"]:
        raise HTTPException(status_code=403, detail="Schedule belongs to another project")
    update_schedule_status(schedule_id, data.status)
    return {"schedule": get_schedule(schedule_id), "message": "Schedule updated"}
