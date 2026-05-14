"""
User Agent Execution API: install, configure, run, and monitor marketplace agents.

Endpoints:
  POST   /installations           - Install an agent (project-scoped)
  GET    /installations           - List installed agents
  GET    /installations/{id}      - Get installation + schema
  PATCH  /installations/{id}      - Update configuration
  POST   /installations/{id}/run   - Run agent (manual)
  GET    /installations/{id}/runs  - Run history
  POST   /installations/{id}/schedules - Create schedule
  GET    /installations/{id}/schedules - List schedules
  PATCH  /schedules/{id}          - Update schedule status
  GET    /dashboard               - Dashboard: installations, run history, usage costs
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import require_project_context
from api.schemas.task_responses import InstallationRunResponse
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
from database.usage_records import get_aggregated
from database.agent_pricing import get_price as get_agent_price
from engine.quota_checker import check_quota
from task_queue.task_queue import enqueue_task


router = APIRouter(prefix="/installations", tags=["installations"])


class InstallAgentRequest(BaseModel):
    agent_name: str = Field(..., description="Agent name from marketplace")


class UpdateConfigurationRequest(BaseModel):
    configuration: dict = Field(..., description="Key-value config matching agent input_schema")


class CreateScheduleRequest(BaseModel):
    cron_expression: str = Field(..., description="Cron expression, e.g. '0 9 * * *' for daily 9am")
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


@router.post("")
def post_install(
    data: InstallAgentRequest,
    context: dict = Depends(require_project_context),
):
    """Install an agent from the marketplace. Configuration is initialized from agent defaults."""
    project_id = context["project_id"]
    try:
        installation = install_agent(project_id, data.agent_name)
        return {"installation": installation, "message": "Agent installed"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
def list_installations(context: dict = Depends(require_project_context)):
    """List all installed agents for the project."""
    project_id = context["project_id"]
    return {"installations": list_installations_by_project(project_id)}


# Dashboard at /dashboard (separate router so path is /dashboard not /installations/dashboard)
dashboard_router = APIRouter(tags=["dashboard"])


@dashboard_router.get("/dashboard")
def get_dashboard(context: dict = Depends(require_project_context)):
    """
    Simple dashboard: installed agents, recent run history, execution status, usage costs.
    No infrastructure concepts (workers, queues, regions) are exposed.
    """
    project_id = context["project_id"]
    try:
        installations = list_installations_by_project(project_id)
    except Exception:
        installations = []
    runs_today = 0
    cost_today = 0.0
    recent_runs = []
    for inst in installations:
        try:
            runs = list_runs_by_installation(inst["installation_id"], limit=5)
        except Exception:
            runs = []
        for r in runs:
            recent_runs.append({
                "installation_id": inst["installation_id"],
                "agent_name": inst["agent_name"],
                "run_id": r["run_id"],
                "task_id": r["task_id"],
                "status": r["status"],
                "execution_time_ms": r["execution_time_ms"],
                "created_at": r["created_at"],
            })
    recent_runs.sort(key=lambda x: x["created_at"] or "", reverse=True)
    recent_runs = recent_runs[:20]
    try:
        agg = get_aggregated(project_id=project_id)
    except Exception:
        agg = {"total_runs": 0, "total_agent_cost": 0, "runs_per_agent": []}
    today_str = None
    try:
        from datetime import datetime
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
    except Exception:
        pass
    if today_str:
        try:
            day_agg = get_aggregated(project_id=project_id, start_date=today_str, end_date=today_str)
            runs_today = day_agg.get("total_runs", 0)
            cost_today = day_agg.get("total_agent_cost") or 0.0
        except Exception:
            pass
    try:
        from database.usage_records import get_usage_this_month
        month_usage = get_usage_this_month(project_id)
        monthly_usage = {
            "runs_this_month": month_usage.get("runs_this_month", 0),
            "execution_time_this_month_ms": month_usage.get("execution_time_this_month_ms", 0),
        }
    except Exception:
        monthly_usage = {"runs_this_month": 0, "execution_time_this_month_ms": 0}
    # Billing visibility: cost per run from agent_pricing for display (e.g. "Cost per run: $0.01")
    runs_per_agent = list(agg.get("runs_per_agent", []))
    for r in runs_per_agent:
        try:
            pricing = get_agent_price(r.get("agent_name") or "")
            r["cost_per_run"] = float(pricing["price_per_run"]) if pricing else 0.0
            if pricing:
                r["currency"] = pricing.get("currency") or "USD"
        except Exception:
            r["cost_per_run"] = 0.0
            r["currency"] = "USD"

    return {
        "project_id": project_id,
        "installations": installations,
        "recent_runs": recent_runs,
        "runs_today": runs_today,
        "cost_today": round(cost_today, 4),
        "monthly_usage": monthly_usage,
        "total_runs": agg["total_runs"],
        "total_agent_cost": round(agg.get("total_agent_cost") or 0, 4),
        "runs_per_agent": runs_per_agent,
    }


@router.get("/{installation_id}")
def get_one(
    installation_id: int,
    context: dict = Depends(require_project_context),
):
    """Get installation and its input_schema for configuration UI."""
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


@router.patch("/{installation_id}")
def patch_configuration(
    installation_id: int,
    data: UpdateConfigurationRequest,
    context: dict = Depends(require_project_context),
):
    """Update agent configuration. Validates against agent input_schema; required params must be present."""
    project_id = context["project_id"]
    inst = _installation_for_project(installation_id, project_id)
    valid, err = validate_configuration(inst["agent_name"], data.configuration)
    if not valid:
        raise HTTPException(status_code=400, detail=err or "Invalid configuration")
    update_agent_configuration(installation_id, data.configuration)
    return {"installation": get_installation(installation_id), "message": "Configuration updated"}


@router.post("/{installation_id}/run", response_model=InstallationRunResponse)
def run_agent(
    installation_id: int,
    context: dict = Depends(require_project_context),
):
    """
    Run the agent now (manual run). Loads configuration, builds task payload, enqueues task.
    Returns task_id. Result will appear in run history when the task completes.
    """
    project_id = context["project_id"]
    check_quota(project_id)
    inst = _installation_for_project(installation_id, project_id)
    config = inst.get("configuration") or {}
    agent_name = inst["agent_name"]
    payload = {
        "agent": agent_name,
        "task": "Run with configured inputs",
        "input": config,
        "installation_id": installation_id,
    }
    task_id = enqueue_task(payload, project_id=project_id)
    return {
        "message": "Agent run started",
        "task_id": task_id,
        "installation_id": installation_id,
        "agent_name": agent_name,
    }


@router.get("/{installation_id}/runs")
def list_runs(
    installation_id: int,
    limit: int = 50,
    offset: int = 0,
    context: dict = Depends(require_project_context),
):
    """Run history for this installation."""
    project_id = context["project_id"]
    _installation_for_project(installation_id, project_id)
    return {"runs": list_runs_by_installation(installation_id, limit=limit, offset=offset)}


@router.post("/{installation_id}/schedules")
def post_schedule(
    installation_id: int,
    data: CreateScheduleRequest,
    context: dict = Depends(require_project_context),
):
    """Create a schedule to run this agent automatically (cron)."""
    project_id = context["project_id"]
    _installation_for_project(installation_id, project_id)
    schedule_id = create_schedule(installation_id, data.cron_expression, data.status)
    return {"schedule": get_schedule(schedule_id), "message": "Schedule created"}


@router.get("/{installation_id}/schedules")
def list_schedules(
    installation_id: int,
    context: dict = Depends(require_project_context),
):
    """List schedules for this installation."""
    project_id = context["project_id"]
    _installation_for_project(installation_id, project_id)
    return {"schedules": list_schedules_by_installation(installation_id)}


# Schedule-scoped (by schedule_id)
router_schedules = APIRouter(prefix="/schedules", tags=["schedules"])


@router_schedules.patch("/{schedule_id}")
def patch_schedule(
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
