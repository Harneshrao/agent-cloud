"""
Simulation API: sandbox for testing agent teams and workflows.

POST   /simulations              - Create simulation (project_id, scenario_name)
POST   /simulations/{id}/start    - Start: clone state into simulation context
POST   /simulations/{id}/events   - Inject event (event_type, payload)
POST   /simulations/{id}/process-events - Process injected events (triggers -> sim tasks)
GET    /simulations/{id}         - Get run + metrics
GET    /simulations/{id}/events   - List injected events
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.deps import require_project_context
from api.schemas.task_responses import SimulationProcessEventsResponse
from database.simulation import (
    create_simulation,
    get_simulation,
    start_simulation,
    inject_event,
    list_simulation_events,
    process_simulation_events,
)


router = APIRouter(prefix="/simulations", tags=["simulations"])


class CreateSimulationRequest(BaseModel):
    """Request body for POST /simulations."""

    scenario_name: str = Field(..., description="Name of the scenario (e.g. market_crash_stress)")


class InjectEventRequest(BaseModel):
    """Request body for POST /simulations/{id}/events."""

    event_type: str = Field(..., description="Event type (e.g. market_crash)")
    payload: dict = Field(default_factory=dict, description="Event payload (e.g. {\"sector\": \"tech\"})")


def _get_simulation_or_404(simulation_id: int, project_id: int):
    run = get_simulation(simulation_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    if run["project_id"] != project_id:
        raise HTTPException(status_code=403, detail="Simulation belongs to another project")
    return run


@router.get("")
def list_runs(context: dict = Depends(require_project_context)):
    """List simulations for the current project."""
    project_id = context["project_id"]
    from database.simulation import list_simulations_for_project
    return list_simulations_for_project(project_id)


@router.post("")
def create(
    data: CreateSimulationRequest,
    context: dict = Depends(require_project_context),
):
    """Create a new simulation run. Status = 'created'. Call start to clone state."""
    project_id = context["project_id"]
    sim_id = create_simulation(project_id, data.scenario_name)
    run = get_simulation(sim_id)
    return {"simulation_id": sim_id, "simulation": run}


@router.post("/{simulation_id}/start")
def start(
    simulation_id: int,
    context: dict = Depends(require_project_context),
):
    """Start simulation: clone agent_instances, knowledge_graph, agent_memory into simulation context."""
    project_id = context["project_id"]
    _get_simulation_or_404(simulation_id, project_id)
    if not start_simulation(simulation_id):
        raise HTTPException(
            status_code=400,
            detail="Simulation not found or already running/completed",
        )
    return {"status": "running", "simulation": get_simulation(simulation_id)}


@router.post("/{simulation_id}/events")
def inject(
    simulation_id: int,
    data: InjectEventRequest,
    context: dict = Depends(require_project_context),
):
    """Inject an event into the simulation. Agents react using normal event triggers when process-events is called."""
    project_id = context["project_id"]
    _get_simulation_or_404(simulation_id, project_id)
    event_id = inject_event(simulation_id, data.event_type, data.payload)
    return {
        "event_id": event_id,
        "event_type": data.event_type,
        "payload": data.payload,
    }


@router.post("/{simulation_id}/process-events", response_model=SimulationProcessEventsResponse)
def process_events(
    simulation_id: int,
    context: dict = Depends(require_project_context),
):
    """Process all injected events: match triggers and enqueue tasks to simulation (not production)."""
    project_id = context["project_id"]
    run = _get_simulation_or_404(simulation_id, project_id)
    task_ids = process_simulation_events(simulation_id, project_id)
    sim = get_simulation(simulation_id)
    return SimulationProcessEventsResponse(
        tasks_queued=len(task_ids),
        task_ids=task_ids,
        simulation=dict(sim) if sim else {},
    )


@router.get("/{simulation_id}")
def get_run(
    simulation_id: int,
    context: dict = Depends(require_project_context),
):
    """Get simulation run and metrics (tasks_created, workflows_executed, messages_sent, success_rate)."""
    project_id = context["project_id"]
    run = _get_simulation_or_404(simulation_id, project_id)
    return run


@router.get("/{simulation_id}/events")
def list_events(
    simulation_id: int,
    context: dict = Depends(require_project_context),
):
    """List all injected events for this simulation."""
    project_id = context["project_id"]
    _get_simulation_or_404(simulation_id, project_id)
    return list_simulation_events(simulation_id)
