#!/usr/bin/env python3
"""
Wave 1 infra regression checks — run before each alpha tester.

Usage:
  py -3.11 scripts/wave1_infra_check.py
  py -3.11 scripts/wave1_infra_check.py --api http://127.0.0.1:8000

Exits 0 when all checks pass; 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _fail(msg: str) -> None:
    print(f"  FAIL — {msg}")


def _ok(msg: str) -> None:
    print(f"  OK — {msg}")


def _api_json(
    base: str,
    method: str,
    path: str,
    *,
    project_id: Optional[str] = None,
    body: Optional[dict] = None,
    timeout: float = 15.0,
) -> tuple[int, Any]:
    url = f"{base.rstrip('/')}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {
        "User-Agent": "agent-cloud-wave1-infra/1.0",
        "Content-Type": "application/json",
    }
    if project_id:
        headers["X-Project-ID"] = project_id
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            return resp.getcode(), json.loads(raw) if raw else {}
    except HTTPError as e:
        raw = e.read().decode()
        try:
            body_out = json.loads(raw)
        except json.JSONDecodeError:
            body_out = {"detail": raw}
        return e.code, body_out


def check_schema() -> bool:
    print("Schema (Alembic + Wave 1 tables)")
    try:
        from api.migration_check import (
            get_db_revision,
            get_head_revision,
            missing_required_tables,
        )

        head = get_head_revision()
        db_rev = get_db_revision()
        if db_rev != head:
            _fail(f"Alembic drift db={db_rev!r} head={head!r} — run alembic upgrade head")
            return False
        missing = missing_required_tables()
        if missing:
            _fail(f"Missing tables: {', '.join(missing)}")
            return False
        _ok(f"At head {head}")
        return True
    except Exception as e:
        _fail(str(e)[:160])
        return False


def check_regions_query() -> bool:
    print("Regions routing table")
    try:
        from database.regions import list_active_regions

        regions = list_active_regions()
        if not regions:
            _fail("No active regions seeded")
            return False
        _ok(f"{len(regions)} region(s): {', '.join(r['region_id'] for r in regions)}")
        return True
    except Exception as e:
        _fail(str(e)[:160])
        return False


def _reconcile_stale_running_tasks() -> int:
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
        return int(result.rowcount or 0)


def check_api_flow(base: str) -> bool:
    print("API E2E (deploy -> run -> trace -> key -> second run)")
    cleared = _reconcile_stale_running_tasks()
    if cleared:
        print(f"  (cleared {cleared} stale running task(s))")
    pid: Optional[str] = None
    try:
        _, body = _api_json(base, "GET", "/projects")
        projects = body.get("projects") or []
        if projects:
            pid = projects[0]["id"]
        else:
            _, body = _api_json(base, "POST", "/projects", body={"name": "Wave1 infra check"})
            pid = body["project"]["id"]
    except Exception as e:
        _fail(f"Project context: {e}")
        return False

    dep_id: Optional[str] = None
    code, body = _api_json(
        base,
        "POST",
        "/deployments/onboarding/sample/sample_echo",
        project_id=pid,
        timeout=30.0,
    )
    if code == 409:
        detail = body.get("detail") if isinstance(body.get("detail"), dict) else body
        dep = (detail or {}).get("deployment") or {}
        dep_id = dep.get("deployment_id")
        _ok(f"Duplicate deploy returned 409 (reusing {str(dep_id)[:8]}…)")
    elif code >= 400:
        _fail(f"Deploy sample_echo HTTP {code}: {body}")
        return False
    else:
        dep_id = body.get("deployment", {}).get("deployment_id")
        _ok(f"Deployed {str(dep_id)[:8]}…")

    if not dep_id:
        _fail("No deployment_id")
        return False

    code, body = _api_json(
        base,
        "POST",
        f"/deployments/{dep_id}/run",
        project_id=pid,
        body={"input": {"message": "wave1 infra check"}},
    )
    if code >= 400:
        _fail(f"Run task HTTP {code}: {body}")
        return False
    task_id = body.get("task_id")
    _ok(f"Task queued {task_id}")

    final = "unknown"
    for _ in range(30):
        _, tb = _api_json(base, "GET", f"/observability/tasks/{task_id}", project_id=pid)
        final = tb.get("status") or (tb.get("task") or {}).get("status") or "unknown"
        if final in ("completed", "failed", "dead", "error"):
            break
        time.sleep(1)
    if final != "completed":
        _fail(f"First run status={final}")
        return False
    _ok(f"First run completed")

    code, body = _api_json(
        base,
        "POST",
        f"/deployments/{dep_id}/run",
        project_id=pid,
        body={"input": {"message": "wave1 second run"}},
    )
    if code >= 400:
        _fail(f"Second run HTTP {code}: {body}")
        return False
    task2 = body.get("task_id")
    status2 = "unknown"
    for _ in range(30):
        _, tb = _api_json(base, "GET", f"/observability/tasks/{task2}", project_id=pid)
        status2 = tb.get("status") or (tb.get("task") or {}).get("status") or "unknown"
        if status2 in ("completed", "failed", "dead", "error"):
            break
        time.sleep(1)
    if status2 != "completed":
        _fail(f"Second run status={status2}")
        return False
    _ok("Second run completed")

    code, body = _api_json(base, "POST", "/api-keys", body={"name": "wave1 probe"})
    if code >= 400:
        _fail(f"API key create HTTP {code}: {body}")
        return False
    if not body.get("key"):
        _fail("API key create returned no key")
        return False
    _ok("API key created")

    code, body = _api_json(
        base,
        "POST",
        "/deployments/onboarding/sample/sample_echo",
        project_id=pid,
    )
    if code != 409:
        _fail(f"Expected 409 on re-deploy, got {code}")
        return False
    detail = body.get("detail") if isinstance(body.get("detail"), dict) else body
    msg = (detail or {}).get("message", "")
    if "already active" not in msg.lower():
        _fail(f"409 message unexpected: {msg!r}")
        return False
    _ok("Re-deploy sample_echo returns 409")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Wave 1 infra regression checks")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--schema-only", action="store_true", help="Skip API E2E")
    args = parser.parse_args()

    print("")
    print("Wave 1 infra check")
    print("=" * 50)

    ok = check_schema()
    ok = check_regions_query() and ok

    if not args.schema_only:
        try:
            code, _ = _api_json(args.api, "GET", "/health", timeout=5.0)
            if code >= 400:
                _fail(f"API health HTTP {code}")
                ok = False
            else:
                ok = check_api_flow(args.api) and ok
        except URLError as e:
            _fail(f"API unreachable at {args.api}: {e.reason}")
            ok = False

    print("=" * 50)
    if ok:
        print("  ALL CHECKS PASSED — ready for User #2")
    else:
        print("  BLOCKED — fix failures before next alpha tester")
    print("")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
