#!/usr/bin/env python3
"""
Pre-flight local dev health check.

Usage:
  py -3.11 scripts/dev_doctor.py              # quick doctor
  py -3.11 scripts/dev_doctor.py --deep        # include API component probes
  py -3.11 scripts/dev_doctor.py --readiness   # alpha tester readiness (E2E smoke)
  py -3.11 scripts/dev_doctor.py --clean       # kill hung dashboard PIDs (dev only)

Also: make doctor | make readiness | make clean-stale
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.dev_health import (  # noqa: E402
    CheckResult,
    detect_stale_processes,
    kill_pids,
    print_report,
    resolve_api_base,
    run_preflight_checks,
)


def _api_json(method: str, path: str, *, project_id: Optional[str] = None, body: Optional[dict] = None, timeout: float = 10.0):
    base, _ = resolve_api_base()
    url = f"{base}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "User-Agent": "agent-cloud-dev-doctor/1.0",
        "Content-Type": "application/json",
    }
    if project_id:
        headers["X-Project-ID"] = project_id
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=timeout) as resp:
        return resp.getcode(), json.loads(resp.read().decode())


def run_alpha_readiness() -> bool:
    """Full smoke: deploy → run → trace → api keys."""
    print("")
    print("Agent Cloud — alpha readiness check")
    print("=" * 50)

    checks: list[CheckResult] = []
    results = run_preflight_checks(include_deep=True)
    stale = detect_stale_processes()
    preflight_ok = all(r.passed for r in results) and not stale.warnings
    if not preflight_ok:
        print_report(results, stale)
        print("  BLOCKED — fix preflight before E2E smoke")
        print("=" * 50)
        return False

    schema = _check_db_schema()
    checks.append(schema)
    if not schema.passed:
        _print_readiness(checks, blocked=True)
        return False

    stale = _reconcile_stale_running_tasks()
    checks.append(stale)

    base, _ = resolve_api_base()
    pid: Optional[str] = None

    try:
        _, body = _api_json("GET", "/projects")
        projects = body.get("projects") or []
        if projects:
            pid = projects[0]["id"]
            checks.append(CheckResult("Project context", True, pid))
        else:
            _, body = _api_json("POST", "/projects", body={"name": "Readiness check"})
            pid = body["project"]["id"]
            checks.append(CheckResult("Project context", True, f"created {pid}"))
    except Exception as e:
        checks.append(CheckResult("Project context", False, str(e)[:120]))
        _print_readiness(checks, blocked=True)
        return False

    dep_id: Optional[str] = None
    try:
        _, body = _api_json("GET", "/deployments", project_id=pid)
        active = [d for d in (body.get("deployments") or []) if d.get("status") == "active"]
        if active:
            dep_id = active[0]["deployment_id"]
            checks.append(CheckResult("Deploy sample echo", True, f"reusing {dep_id[:8]}…"))
        else:
            code, body = _api_json(
                "POST",
                "/deployments/onboarding/sample/sample_echo",
                project_id=pid,
                timeout=30.0,
            )
            if code >= 400:
                checks.append(CheckResult("Deploy sample echo", False, body.get("detail", str(body))[:120]))
            else:
                dep_id = body["deployment"]["deployment_id"]
                checks.append(CheckResult("Deploy sample echo", True, dep_id[:8] + "…"))
    except URLError as e:
        checks.append(CheckResult("Deploy sample echo", False, str(e.reason)[:120]))
    except Exception as e:
        checks.append(CheckResult("Deploy sample echo", False, str(e)[:120]))

    task_id: Optional[str] = None
    if dep_id:
        try:
            code, body = _api_json(
                "POST",
                f"/deployments/{dep_id}/run",
                project_id=pid,
                body={"input": {"message": "readiness check"}},
                timeout=15.0,
            )
            if code >= 400:
                checks.append(CheckResult("Run sample task", False, str(body)[:120]))
            else:
                task_id = body.get("task_id")
                checks.append(CheckResult("Run sample task", True, str(task_id)[:36]))
        except Exception as e:
            checks.append(CheckResult("Run sample task", False, str(e)[:120]))

    if task_id:
        final_status = "unknown"
        try:
            for i in range(30):
                _, body = _api_json("GET", f"/observability/tasks/{task_id}", project_id=pid)
                final_status = body.get("status") or (body.get("task") or {}).get("status") or "unknown"
                if final_status in ("completed", "failed", "dead", "error"):
                    break
                time.sleep(1)
            ok = final_status == "completed"
            checks.append(
                CheckResult(
                    "Execution trace",
                    ok,
                    f"status={final_status}",
                    "" if ok else "Check worker logs; py -3.11 scripts/dev_doctor.py --deep",
                )
            )
            if ok:
                _, logs_body = _api_json("GET", f"/observability/tasks/{task_id}/logs", project_id=pid)
                n = len(logs_body.get("logs") or logs_body.get("events") or [])
                checks.append(CheckResult("Trace logs", True, f"{n} log line(s)"))
                if dep_id:
                    code2, body2 = _api_json(
                        "POST",
                        f"/deployments/{dep_id}/run",
                        project_id=pid,
                        body={"input": {"message": "readiness second run"}},
                        timeout=15.0,
                    )
                    task2 = body2.get("task_id") if code2 < 400 else None
                    if task2:
                        status2 = "unknown"
                        for _ in range(30):
                            _, tb = _api_json("GET", f"/observability/tasks/{task2}", project_id=pid)
                            status2 = tb.get("status") or (tb.get("task") or {}).get("status") or "unknown"
                            if status2 in ("completed", "failed", "dead", "error"):
                                break
                            time.sleep(1)
                        ok2 = status2 == "completed"
                        checks.append(
                            CheckResult(
                                "Second run (repeat loop)",
                                ok2,
                                f"status={status2}",
                                "" if ok2 else "Repeat activation path broken",
                            )
                        )
                    else:
                        checks.append(
                            CheckResult(
                                "Second run (repeat loop)",
                                False,
                                str(body2)[:120],
                            )
                        )
        except Exception as e:
            checks.append(CheckResult("Execution trace", False, str(e)[:120]))

    try:
        code, body = _api_json("GET", "/api-keys")
        if code >= 400:
            checks.append(CheckResult("API keys page", False, str(body)[:120]))
        else:
            checks.append(CheckResult("API keys page", True, f"{body.get('count', 0)} key(s) listed"))
        # Create is optional — table may be missing on old DBs
        try:
            code, body = _api_json("POST", "/api-keys", body={"name": "readiness probe"})
            if code < 400:
                checks.append(CheckResult("API key create", True, "ok"))
            else:
                checks.append(
                    CheckResult(
                        "API key create",
                        False,
                        str(body)[:120],
                        "Run: alembic upgrade head (api_keys table)",
                    )
                )
        except Exception as e:
            checks.append(CheckResult("API key create", False, str(e)[:120], "alembic upgrade head"))
    except Exception as e:
        checks.append(CheckResult("API keys page", False, str(e)[:120]))

    # Dashboard reachability
    from scripts.dev_health import check_dashboard

    checks.append(check_dashboard())

    blocked = not all(c.passed for c in checks)
    _print_readiness(checks, blocked=blocked)
    return not blocked


def _reconcile_stale_running_tasks() -> CheckResult:
    """Fail orphaned running tasks so concurrent quota is not poisoned."""
    try:
        from sqlalchemy import update

        from database.models import Task, TaskStatus
        from database.session import SessionLocal

        with SessionLocal() as session:
            result = session.execute(
                update(Task)
                .where(Task.status == TaskStatus.running)
                .values(status=TaskStatus.failed)
            )
            session.commit()
            n = int(result.rowcount or 0)
        if n:
            return CheckResult(
                "Stale running tasks cleared",
                True,
                f"{n} task(s) marked failed (were blocking concurrent quota)",
            )
        return CheckResult("Stale running tasks cleared", True, "none")
    except Exception as e:
        return CheckResult(
            "Stale running tasks cleared",
            False,
            str(e)[:120],
            "Check tasks table and worker processes",
        )


def _check_db_schema() -> CheckResult:
    try:
        from api.migration_check import (
            get_db_revision,
            get_head_revision,
            missing_required_tables,
        )

        head = get_head_revision()
        db_rev = get_db_revision()
        if db_rev != head:
            return CheckResult(
                "DB schema (Alembic head)",
                False,
                f"db={db_rev!r} expected={head!r}",
                "Run: alembic upgrade head",
            )
        missing = missing_required_tables()
        if missing:
            return CheckResult(
                "DB schema (Wave 1 tables)",
                False,
                f"missing: {', '.join(missing)}",
                "Run: alembic upgrade head",
            )
        return CheckResult("DB schema (Alembic head)", True, head)
    except Exception as e:
        return CheckResult(
            "DB schema",
            False,
            str(e)[:120],
            "Set DATABASE_URL and run: alembic upgrade head",
        )


def _print_readiness(checks: list[CheckResult], *, blocked: bool) -> None:
    for c in checks:
        print(c.line())
        if not c.passed and c.hint:
            print(f"         -> {c.hint}")
    print("=" * 50)
    if blocked:
        print("  BLOCKED — not ready for alpha tester")
    else:
        print("  READY FOR TESTER")
    print("")


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent Cloud local dev health doctor")
    parser.add_argument("--deep", action="store_true", help="Include API deep component probes")
    parser.add_argument(
        "--readiness",
        action="store_true",
        help="Alpha tester readiness (preflight + E2E smoke)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Kill hung dashboard processes (dev only)",
    )
    args = parser.parse_args()

    if args.clean:
        stale = detect_stale_processes(auto_mark_hung=True)
        if not stale.pids_to_kill:
            print("No hung dashboard processes detected.")
            if stale.warnings:
                for w in stale.warnings:
                    print(f"  WARN: {w}")
            return 0
        print("Killing stale PIDs:", stale.pids_to_kill)
        for line in kill_pids(stale.pids_to_kill):
            print(" ", line)
        print("Done. Restart with: py -3.11 run_all.py")
        return 0

    if args.readiness:
        return 0 if run_alpha_readiness() else 1

    stale = detect_stale_processes()
    results = run_preflight_checks(include_deep=args.deep)
    ok = print_report(results, stale)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
