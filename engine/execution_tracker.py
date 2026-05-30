from __future__ import annotations

import time
from typing import Any, Dict

from database.db import db
from database.task_graph import get_task_text_and_status
from database import usage_records
from database.agent_pricing import get_price as get_agent_price
from database import agent_revenue as agent_revenue_db
from database.agent_usage_stats import increment_agent_run


# Start times for computing execution_time_ms on completion: (task_id, agent_name) -> perf_counter()
_start_times: Dict[tuple, float] = {}


def _log_event(task_id: int, agent_name: str, status: str, error: Any = None) -> None:
    """
    Internal helper to log a structured execution event.

    Events are both printed to stdout and stored using the existing
    db.store_agent_run method so they are queryable later.
    """
    event: Dict[str, Any] = {
        "task_id": task_id,
        "agent": agent_name,
        "status": status,
    }

    if error is not None:
        event["error"] = str(error)

    print(f"[ExecutionTracker] {event}")

    # Reuse the existing agent_runs table for execution events.
    db.store_agent_run(task_id, agent_name, event)


def start_agent(agent_name: str, task_id: int) -> None:
    """
    Mark the beginning of an agent's execution.
    Records start time for usage metering (execution_time_ms) when finish_agent is called.
    """
    _start_times[(task_id, agent_name)] = time.perf_counter()
    _log_event(task_id, agent_name, status="running")


def finish_agent(agent_name: str, task_id: int) -> None:
    """
    Mark successful completion of an agent's execution.
    Records usage: project_id, task_id, agent_name, execution_time_ms, agent_cost (price_per_run).
    """
    start = _start_times.pop((task_id, agent_name), None)
    execution_time_ms = 0
    if start is not None:
        execution_time_ms = int((time.perf_counter() - start) * 1000)

    pricing = get_agent_price(agent_name)
    agent_cost = float(pricing["price_per_run"]) if pricing else 0.0

    task_info = get_task_text_and_status(task_id)
    project_id = task_info.get("project_id") if task_info else None
    installation_id = None
    if task_info and task_info.get("task_text"):
        from services.task_payload import parse_payload as _parse_payload
        parsed = _parse_payload(task_info["task_text"])
        installation_id = parsed.get("installation_id")
    if installation_id is not None:
        try:
            from database.agent_run_results import record_run
            record_run(
                installation_id=int(installation_id),
                task_id=task_id,
                status="completed",
                execution_time_ms=execution_time_ms,
                output=None,
            )
        except Exception as e:
            print(f"[ExecutionTracker] agent_run_results.record_run failed: {e}")
    usage_records.record_usage(
        project_id=project_id,
        task_id=task_id,
        agent_name=agent_name,
        execution_time_ms=execution_time_ms,
        tokens_used=0,
        agent_cost=agent_cost,
    )

    try:
        increment_agent_run(agent_name)
    except Exception as e:
        print(f"[ExecutionTracker] increment_agent_run failed: {e}")

    # Revenue sharing: record split and credit developer balance
    if agent_cost > 0 and pricing:
        developer_user_id = pricing.get("developer_user_id")
        try:
            agent_revenue_db.record_revenue(agent_name, agent_cost, developer_user_id)
        except Exception as e:
            print(f"[ExecutionTracker] Revenue record failed: {e}")

    # Developer economy (80/20): if agent is in published_agents, record earning and install stats
    if agent_cost > 0:
        try:
            from database.developer_economy import (
                get_published_agent_by_name,
                record_earning,
                record_run_and_revenue,
                DEVELOPER_SHARE_RATIO,
            )
            pub = get_published_agent_by_name(agent_name)
            if pub:
                developer_share = round(agent_cost * DEVELOPER_SHARE_RATIO, 4)
                record_earning(
                    developer_id=pub["developer_id"],
                    agent_id=pub["agent_id"],
                    run_id=task_id,
                    amount=developer_share,
                    currency=pub.get("currency") or "USD",
                )
                record_run_and_revenue(pub["agent_id"], agent_cost)
        except Exception as e:
            print(f"[ExecutionTracker] Developer economy record failed: {e}")

    # Trust metrics: record success for ranking and safety
    try:
        from database.agent_production_hardening import record_run_success, check_run_spike_and_record
        from database.developer_economy import get_published_agent_by_name
        pub = get_published_agent_by_name(agent_name)
        agent_id = pub["agent_id"] if pub else None
        record_run_success(agent_name, execution_time_ms, agent_id=agent_id)
        if agent_id:
            check_run_spike_and_record(agent_id, agent_name)
    except Exception:
        pass

    # Performance logging: agent_execution_metrics for trust scoring and ranking
    try:
        from database.agent_execution_metrics import record_execution_metric
        from database.developer_economy import get_published_agent_by_name
        pub = get_published_agent_by_name(agent_name)
        record_execution_metric(
            agent_id=pub["agent_id"] if pub else None,
            version=None,
            task_id=task_id,
            runtime_ms=execution_time_ms,
            memory_used=None,
            success=True,
        )
    except Exception:
        pass

    _log_event(task_id, agent_name, status="completed")


def fail_agent(agent_name: str, task_id: int, error: Any) -> None:
    """
    Mark a failed agent execution, capturing the error.
    Records run result for user installations (installation_id in task payload).
    """
    _start_times.pop((task_id, agent_name), None)
    task_info = get_task_text_and_status(task_id)
    installation_id = None
    if task_info and task_info.get("task_text"):
        from services.task_payload import parse_payload as _parse_payload
        parsed = _parse_payload(task_info["task_text"])
        installation_id = parsed.get("installation_id")
    if installation_id is not None:
        try:
            from database.agent_run_results import record_run
            record_run(
                installation_id=int(installation_id),
                task_id=task_id,
                status="failed",
                execution_time_ms=0,
                output={"error": str(error)},
            )
        except Exception as e:
            print(f"[ExecutionTracker] agent_run_results.record_run failed: {e}")
    # Trust metrics: record failure
    try:
        from database.agent_production_hardening import record_run_failure
        from database.developer_economy import get_published_agent_by_name
        pub = get_published_agent_by_name(agent_name)
        record_run_failure(agent_name, agent_id=pub["agent_id"] if pub else None)
    except Exception:
        pass
    # Performance logging: record failed execution
    try:
        from database.agent_execution_metrics import record_execution_metric
        from database.developer_economy import get_published_agent_by_name
        pub = get_published_agent_by_name(agent_name)
        record_execution_metric(
            agent_id=pub["agent_id"] if pub else None,
            version=None,
            task_id=task_id,
            runtime_ms=0,
            memory_used=None,
            success=False,
        )
    except Exception:
        pass
    _log_event(task_id, agent_name, status="failed", error=error)
