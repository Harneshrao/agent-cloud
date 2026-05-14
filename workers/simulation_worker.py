"""
Simulation Worker: executes simulation tasks using cloned state only.

Runs a loop:
  1. fetch_next_simulation_task(simulation_id)
  2. Execute agent with simulation context (cloned instances, memory, KG)
  3. Update metrics (tasks_completed / tasks_failed, messages_sent, workflows_executed)

Does not touch production tasks, agent_instances, agent_memory, or knowledge_graph.

Usage:
  Set SIMULATION_ID in the environment, or pass as first argument.
  python -m workers.simulation_worker [simulation_id]
"""

from __future__ import annotations

import os
import sys
import time
import uuid

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.simulation import (
    fetch_next_simulation_task,
    get_simulation,
)
from orchestrator.orchestrator import run_single_agent_node_simulation


def run_loop(simulation_id: int) -> None:
    """Run the simulation worker loop for the given simulation_id."""
    run = get_simulation(simulation_id)
    if not run:
        print(f"Simulation {simulation_id} not found. Exiting.")
        return
    if run.get("status") not in ("running", "created"):
        print(f"Simulation {simulation_id} status is {run.get('status')}. Exiting.")
        return
    raw_pid = run["project_id"]
    if isinstance(raw_pid, uuid.UUID):
        project_id = raw_pid
    else:
        project_id = uuid.UUID(str(raw_pid))
    print(f"Simulation worker started for simulation_id={simulation_id} project_id={project_id}")
    print("Fetching simulation tasks (cloned state only)...\n")

    while True:
        task = fetch_next_simulation_task(simulation_id)
        if not task:
            time.sleep(2)
            continue

        sim_task_id = task["id"]
        task_text = task.get("task", "")
        agent_name = task.get("agent") or ""
        agent_instance_id = task.get("agent_instance_id")

        print(f"Processing simulation task {sim_task_id}: agent={agent_name} task={task_text[:60]}...")
        try:
            run_single_agent_node_simulation(
                simulation_id=simulation_id,
                sim_task_id=sim_task_id,
                task=task_text,
                agent_name=agent_name,
                project_id=project_id,
                agent_instance_id=agent_instance_id,
            )
            print(f"Simulation task {sim_task_id} completed. Metrics updated.")
        except Exception as e:
            print(f"Simulation task {sim_task_id} failed: {e}")
            from database.simulation import complete_simulation_task
            try:
                complete_simulation_task(simulation_id, sim_task_id, success=False)
            except Exception:
                pass
        print("Waiting for next simulation task...\n")


def main() -> None:
    simulation_id_str = os.environ.get("SIMULATION_ID", "").strip() or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not simulation_id_str:
        print("Usage: set SIMULATION_ID or run: python -m workers.simulation_worker <simulation_id>")
        sys.exit(1)
    try:
        simulation_id = int(simulation_id_str)
    except ValueError:
        print("SIMULATION_ID must be an integer.")
        sys.exit(1)
    run_loop(simulation_id)


if __name__ == "__main__":
    main()
