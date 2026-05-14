import sys
import os
import threading
import time
import uuid
import json as _json

# Fix Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_runtime.loader import discover_agents

discover_agents()

from orchestrator.orchestrator import run_pipeline, run_single_agent_node
from services.task_service import fetch_next_task, update_task_heartbeat, update_task_status
from engine.safe_execution import run_with_timeout, AgentTimeoutError, MemoryLimitExceededError
from database.db import db
from engine.worker_registry import register_worker, set_capabilities, get_capabilities, heartbeat, get_worker_type
from engine.dag_scheduler import on_node_completed, on_node_failed
from agent_runtime.execution_engine import execute_agent_task
from database.workflow_checkpoints import set_running as checkpoint_set_running
from database.task_idempotency import (
    try_claim,
    set_completed,
    get_result,
    delete_record,
)
from database.dead_letter import (
    MAX_RETRIES,
    increment_retry_count,
    insert_dead_letter,
)

def _task_to_payload(task):
    """Build task_text (JSON payload) from task dict for re-enqueue or DLQ storage."""
    payload = {
        "task": task.get("task", ""),
        "agent": task.get("agent"),
        "runtime": task.get("runtime"),
        "workflow_id": task.get("workflow_id"),
        "node_id": task.get("node_id"),
        "deps": task.get("deps"),
        "required_capabilities": task.get("required_capabilities"),
        "priority": task.get("priority"),
        "idempotency_key": task.get("idempotency_key"),
        "target_region": task.get("target_region"),
        "agent_instance_id": task.get("agent_instance_id"),
        "installation_id": task.get("installation_id"),
        "input": task.get("input"),
    }
    return _json.dumps({k: v for k, v in payload.items() if v is not None})


def _resolve_agent_instance(agent_instance_id):
    """Resolve agent instance to agent_name and instance state. Returns (agent_name, state) or (None, None)."""
    try:
        from database.agent_instances import get_instance
        inst = get_instance(agent_instance_id)
        if inst is None:
            return None, None
        return inst.get("agent_name"), inst.get("state") or {}
    except Exception:
        return None, None


worker_id = "ZENIO-" + str(uuid.uuid4())[:4]
worker_region = os.environ.get("WORKER_REGION", "").strip() or None
worker_type = (os.environ.get("WORKER_TYPE", "").strip() or "").lower() or None
register_worker(worker_id, region=worker_region, worker_type=worker_type)
# Worker capability scheduling: advertise capabilities from env (e.g. WORKER_CAPABILITIES=python,gpu,browser)
_caps_env = os.environ.get("WORKER_CAPABILITIES", "").strip()
worker_capabilities = [c.strip() for c in _caps_env.split(",") if c.strip()] if _caps_env else None
if worker_capabilities:
    set_capabilities(worker_id, worker_capabilities)

# Observability: report tasks_running every 10 seconds (single-threaded worker: 0 or 1).
_tasks_running = 0
_current_task_id = None
_tasks_running_lock = threading.Lock()


def _heartbeat_loop():
    while True:
        time.sleep(10)
        with _tasks_running_lock:
            n = _tasks_running
            task_id = _current_task_id
        try:
            heartbeat(worker_id, tasks_running=n, region=worker_region)
        except Exception:
            pass
        if task_id is not None:
            try:
                update_task_heartbeat(task_id)
            except Exception:
                pass


threading.Thread(target=_heartbeat_loop, daemon=True).start()

print("Worker started")
print("Waiting for tasks...\n")

while True:
    task = fetch_next_task(worker_capabilities=worker_capabilities, worker_region=worker_region, worker_type=worker_type)

    if not task:
        print("Waiting for tasks...")
        time.sleep(3)
        continue

    with _tasks_running_lock:
        _tasks_running = 1
        _current_task_id = task["id"]

    workflow_id = task.get("workflow_id")
    node_id = task.get("node_id")
    idempotency_key = task.get("idempotency_key")
    if idempotency_key is None:
        if workflow_id is not None and node_id is not None:
            idempotency_key = f"{workflow_id}:{node_id}"
        else:
            idempotency_key = str(task["id"])

    claimed, existing_status = try_claim(idempotency_key, task["id"])
    if not claimed:
        if existing_status == "completed":
            stored = get_result(idempotency_key)
            update_task_status(task["id"], "completed")
            if stored is not None:
                db.store_result(task["id"], stored)
            print("Task skipped (idempotent: already completed)")
        else:
            print("Task skipped (idempotent: another worker running)")
        with _tasks_running_lock:
            _tasks_running = 0
            _current_task_id = None
        print("Waiting for tasks...\n")
        continue

    try:
        agent_instance_id = task.get("agent_instance_id")
        instance_state = None
        agent_name = task.get("agent")
        if agent_instance_id:
            resolved_name, instance_state = _resolve_agent_instance(agent_instance_id)
            if resolved_name and not agent_name:
                agent_name = resolved_name
        if instance_state is None:
            instance_state = {}
        if task.get("input") is not None:
            instance_state["input"] = task["input"]
        if agent_name is None:
            agent_name = ""

        if workflow_id is not None and node_id is not None:
            wf_uuid = uuid.UUID(str(workflow_id))
            task_uuid = uuid.UUID(str(task["id"]))
            print(f"Processing DAG node: {node_id} (workflow {wf_uuid})")
            checkpoint_set_running(wf_uuid, node_id)
            out = run_with_timeout(
                lambda: run_single_agent_node(
                    task_uuid, task["task"], agent_name,
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
            on_node_completed(wf_uuid, node_id, task_uuid, agent_name, result)
            update_task_status(task_uuid, "completed")
            set_completed(idempotency_key, result)
            if task.get("installation_id") is not None:
                try:
                    from database.agent_run_results import update_output
                    update_output(task_uuid, result)
                except Exception:
                    pass
            print("Node completed")
        else:
            print(f"Processing task: {task['task']}")
            runtime = task.get("runtime")
            if runtime == "v2":
                project_id = db.get_task_project_id(task["id"])
                inputs = task.get("input") or {}
                _final = run_with_timeout(
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
                    _final, state_snapshot = out
                    if agent_instance_id and state_snapshot is not None:
                        try:
                            from database.agent_instances import update_state
                            update_state(agent_instance_id, state_snapshot)
                        except Exception:
                            pass
                else:
                    _final = out
            update_task_status(task["id"], "completed")
            set_completed(idempotency_key, _final)
            if task.get("installation_id") is not None:
                try:
                    from database.agent_run_results import update_output
                    update_output(task["id"], _final)
                except Exception:
                    pass
            print("Task completed")

    except (AgentTimeoutError, MemoryLimitExceededError) as e:
        delete_record(idempotency_key)
        task_id = uuid.UUID(str(task["id"]))
        retry_count = increment_retry_count(task_id)
        task_payload = _task_to_payload(task)
        if retry_count >= MAX_RETRIES:
            insert_dead_letter(
                task_id=task_id,
                task_payload=task_payload,
                error=str(e),
                retry_count=retry_count,
                workflow_id=task.get("workflow_id"),
                node_id=task.get("node_id"),
                agent_name=task.get("agent"),
            )
            if task.get("workflow_id") is not None and task.get("node_id") is not None:
                try:
                    on_node_failed(
                        uuid.UUID(str(task["workflow_id"])),
                        task["node_id"],
                        task_id,
                        e,
                    )
                except Exception:
                    pass
            update_task_status(task_id, "failed")
            print(f"Task failed (security limit, moved to DLQ): {e}")
        else:
            db.reset_task_to_pending(task_id)
            try:
                from services.task_service import push_existing_task
                push_existing_task(task_id, task_payload)
            except Exception:
                pass
            print(f"Task failed (security limit, retry {retry_count}/{MAX_RETRIES}): {e}")
    except Exception as e:
        delete_record(idempotency_key)
        task_id = uuid.UUID(str(task["id"]))
        retry_count = increment_retry_count(task_id)
        task_payload = _task_to_payload(task)
        if retry_count >= MAX_RETRIES:
            insert_dead_letter(
                task_id=task_id,
                task_payload=task_payload,
                error=str(e),
                retry_count=retry_count,
                workflow_id=task.get("workflow_id"),
                node_id=task.get("node_id"),
                agent_name=task.get("agent"),
            )
            if task.get("workflow_id") is not None and task.get("node_id") is not None:
                try:
                    on_node_failed(
                        uuid.UUID(str(task["workflow_id"])),
                        task["node_id"],
                        task_id,
                        e,
                    )
                except Exception:
                    pass
            update_task_status(task_id, "failed")
            print(f"Task failed (moved to DLQ after {retry_count} retries): {e}")
        else:
            db.reset_task_to_pending(task_id)
            try:
                from services.task_service import push_existing_task
                push_existing_task(task_id, task_payload)
            except Exception:
                pass
            print(f"Task failed (retry {retry_count}/{MAX_RETRIES}), re-queued: {e}")

    finally:
        with _tasks_running_lock:
            _tasks_running = 0
            _current_task_id = None

    print("Waiting for tasks...\n")
