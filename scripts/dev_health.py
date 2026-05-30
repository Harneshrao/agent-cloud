"""
Local dev health probes — process detection, HTTP checks, recovery hints.

Used by scripts/dev_doctor.py and run_all.py.
"""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple
from urllib.error import URLError
from urllib.request import Request, urlopen

# Repo root on sys.path when invoked as script
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

DEFAULT_API_PORTS = (8000, 8001)
DEFAULT_DASHBOARD_PORT = 3000
DEFAULT_POSTGRES_PORT = 5433
DEFAULT_REDIS_PORT = 6379

HTTP_TIMEOUT_S = 5.0
HUNG_THRESHOLD_S = 5.0


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    hint: str = ""

    def line(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        base = f"  [{mark}] {self.name}"
        if self.detail:
            base += f" - {self.detail}"
        return base


@dataclass
class PortProcess:
    port: int
    pid: int
    state: str = "LISTENING"


@dataclass
class StaleReport:
    warnings: List[str] = field(default_factory=list)
    pids_to_kill: List[int] = field(default_factory=list)
    recovery_commands: List[str] = field(default_factory=list)


def _http_get(url: str, timeout: float = HTTP_TIMEOUT_S) -> Tuple[str, float, Optional[str]]:
    """
    Returns (status, latency_seconds, error).
    status: ok | timeout | refused | error
    """
    import time

    start = time.monotonic()
    req = Request(url, headers={"User-Agent": "agent-cloud-dev-doctor/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            code = resp.getcode()
            elapsed = time.monotonic() - start
            if 200 <= code < 400:
                return "ok", elapsed, None
            return "error", elapsed, f"HTTP {code}"
    except socket.timeout:
        return "timeout", time.monotonic() - start, f"no response within {timeout}s"
    except URLError as e:
        elapsed = time.monotonic() - start
        reason = getattr(e, "reason", e)
        if isinstance(reason, socket.timeout):
            return "timeout", elapsed, f"no response within {timeout}s"
        if isinstance(reason, ConnectionRefusedError):
            return "refused", elapsed, "connection refused"
        return "error", elapsed, str(reason)[:120]
    except Exception as e:
        return "error", time.monotonic() - start, str(e)[:120]


def resolve_api_base() -> Tuple[str, int]:
    for port in DEFAULT_API_PORTS:
        status, _, _ = _http_get(f"http://127.0.0.1:{port}/health", timeout=2.0)
        if status == "ok":
            return f"http://127.0.0.1:{port}", port
    return f"http://127.0.0.1:{DEFAULT_API_PORTS[0]}", DEFAULT_API_PORTS[0]


def pids_on_port(port: int) -> List[PortProcess]:
    """Return PIDs listening on a TCP port (best-effort, cross-platform)."""
    out: List[PortProcess] = []
    if sys.platform == "win32":
        try:
            proc = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            suffix = f":{port}"
            for line in proc.stdout.splitlines():
                if "LISTENING" not in line.upper():
                    continue
                if suffix not in line:
                    continue
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        pid = int(parts[-1])
                        out.append(PortProcess(port=port, pid=pid))
                    except ValueError:
                        pass
        except Exception:
            pass
    else:
        for cmd in (
            ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
            ["fuser", f"{port}/tcp"],
        ):
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
                if proc.returncode == 0 and proc.stdout.strip():
                    for token in re.split(r"[\s,]+", proc.stdout.strip()):
                        if token.isdigit():
                            out.append(PortProcess(port=port, pid=int(token)))
                    break
            except FileNotFoundError:
                continue
    # Deduplicate PIDs
    seen: set[int] = set()
    deduped: List[PortProcess] = []
    for pp in out:
        if pp.pid not in seen:
            seen.add(pp.pid)
            deduped.append(pp)
    return deduped


def process_name(pid: int) -> str:
    if sys.platform == "win32":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            line = proc.stdout.strip().splitlines()
            if line:
                return line[0].split(",")[0].strip('"').lower()
        except Exception:
            pass
    else:
        try:
            proc = subprocess.run(
                ["ps", "-p", str(pid), "-o", "comm="],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if proc.stdout.strip():
                return proc.stdout.strip().lower()
        except Exception:
            pass
    return "unknown"


def kill_pid_cmd(pid: int) -> str:
    if sys.platform == "win32":
        return f"taskkill /PID {pid} /F"
    return f"kill -9 {pid}"


def detect_stale_processes(
    *,
    dashboard_port: int = DEFAULT_DASHBOARD_PORT,
    api_ports: Tuple[int, ...] = DEFAULT_API_PORTS,
    auto_mark_hung: bool = True,
) -> StaleReport:
    report = StaleReport()

    # Dashboard hung detection
    dash_pids = pids_on_port(dashboard_port)
    if dash_pids:
        status, elapsed, err = _http_get(f"http://127.0.0.1:{dashboard_port}/", timeout=HUNG_THRESHOLD_S)
        if status == "timeout":
            names = ", ".join(f"{process_name(p.pid)}({p.pid})" for p in dash_pids)
            report.warnings.append(
                f"Dashboard port {dashboard_port} is LISTENING but hung ({elapsed:.1f}s, no response). "
                f"PIDs: {names}"
            )
            if auto_mark_hung:
                report.pids_to_kill.extend(p.pid for p in dash_pids)
        elif status == "refused" and len(dash_pids) > 0:
            report.warnings.append(
                f"Port {dashboard_port} has listeners but connection refused — possible zombie socket."
            )
        if len(dash_pids) > 1:
            report.warnings.append(
                f"Multiple processes on port {dashboard_port}: {[p.pid for p in dash_pids]}"
            )

    for port in api_ports:
        api_pids = pids_on_port(port)
        if len(api_pids) > 1:
            report.warnings.append(f"Multiple listeners on API port {port}: {[p.pid for p in api_pids]}")

    for pid in sorted(set(report.pids_to_kill)):
        report.recovery_commands.append(kill_pid_cmd(pid))

    if report.pids_to_kill:
        report.recovery_commands.append(
            "cd dashboard && npm run dev   # or: py -3.11 run_all.py"
        )

    return report


def kill_pids(pids: List[int]) -> List[str]:
    """Kill PIDs; return log lines."""
    logs: List[str] = []
    for pid in sorted(set(pids)):
        if sys.platform == "win32":
            proc = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            ok = proc.returncode == 0
            logs.append(f"taskkill {pid}: {'ok' if ok else proc.stderr.strip() or proc.stdout.strip()}")
        else:
            proc = subprocess.run(
                ["kill", "-9", str(pid)],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            ok = proc.returncode == 0
            logs.append(f"kill {pid}: {'ok' if ok else proc.stderr.strip()}")
    return logs


def check_postgres_direct() -> CheckResult:
    try:
        from services.health_checks import probe_postgres

        ok, detail = probe_postgres()
        hint = "" if ok else "Start: docker compose up -d postgres"
        return CheckResult("Postgres", ok, detail, hint)
    except Exception as e:
        return CheckResult("Postgres", False, str(e)[:120], "Set DATABASE_URL in .env")


def check_redis_direct() -> CheckResult:
    try:
        from services.health_checks import probe_redis

        ok, detail = probe_redis()
        hint = "" if ok else "Start: docker compose up -d redis"
        return CheckResult("Redis", ok, detail, hint)
    except Exception as e:
        return CheckResult("Redis", False, str(e)[:120], "Start: docker compose up -d redis")


def check_api(api_base: Optional[str] = None) -> CheckResult:
    base = api_base or resolve_api_base()[0]
    status, elapsed, err = _http_get(f"{base}/health", timeout=3.0)
    if status == "ok":
        return CheckResult("API /health", True, f"{base} ({elapsed:.2f}s)")
    hint = "Start: py -3.11 run_all.py  or  py -3.11 run_backend.py"
    if pids_on_port(8000) or pids_on_port(8001):
        hint = "Port in use but unhealthy — try: py -3.11 scripts/dev_doctor.py --clean"
    return CheckResult("API /health", False, err or status, hint)


def check_api_deep(api_base: Optional[str] = None) -> CheckResult:
    base = api_base or resolve_api_base()[0]
    status, elapsed, err = _http_get(f"{base}/health?deep=1", timeout=8.0)
    if status != "ok":
        return CheckResult("API deep health", False, err or status)
    try:
        import json
        from urllib.request import urlopen

        with urlopen(f"{base}/health?deep=1", timeout=8.0) as resp:
            body = json.loads(resp.read().decode())
        components = body.get("components") or {}
        bad = {k: v for k, v in components.items() if v != "ok"}
        if bad:
            parts = ", ".join(f"{k}={v}" for k, v in bad.items())
            return CheckResult("API deep health", False, parts, "See docs/DEV_HEALTHCHECK.md")
        return CheckResult("API deep health", True, f"all components ok ({elapsed:.2f}s)")
    except Exception as e:
        return CheckResult("API deep health", False, str(e)[:120])


def check_dashboard(port: int = DEFAULT_DASHBOARD_PORT) -> CheckResult:
    url = f"http://127.0.0.1:{port}/"
    status, elapsed, err = _http_get(url, timeout=HUNG_THRESHOLD_S)
    if status == "ok":
        return CheckResult("Dashboard", True, f"http://127.0.0.1:{port} ({elapsed:.2f}s)")
    if status == "timeout":
        pids = pids_on_port(port)
        pid_str = ", ".join(str(p.pid) for p in pids) or "?"
        return CheckResult(
            "Dashboard",
            False,
            f"HUNG — no response in {HUNG_THRESHOLD_S}s (PIDs: {pid_str})",
            f"py -3.11 scripts/dev_doctor.py --clean  # then restart dashboard",
        )
    if status == "refused":
        return CheckResult(
            "Dashboard",
            False,
            "not running",
            "Start: py -3.11 run_all.py  or  cd dashboard && npm run dev",
        )
    return CheckResult("Dashboard", False, err or status)


def check_workers() -> CheckResult:
    try:
        from services.health_checks import probe_workers

        ok, detail = probe_workers(within_seconds=60)
        hint = "" if ok else "Start worker: py -3.11 -m workers.canonical_worker (or run_all.py)"
        return CheckResult("Worker heartbeat", ok, detail, hint)
    except Exception as e:
        return CheckResult("Worker heartbeat", False, str(e)[:120])


def check_projects(api_base: Optional[str] = None) -> CheckResult:
    import json

    base = api_base or resolve_api_base()[0]
    try:
        req = Request(
            f"{base}/projects",
            headers={"User-Agent": "agent-cloud-dev-doctor/1.0", "Content-Type": "application/json"},
        )
        with urlopen(req, timeout=5.0) as resp:
            body = json.loads(resp.read().decode())
        n = len(body.get("projects") or [])
        return CheckResult("Projects API", True, f"{n} project(s)")
    except Exception as e:
        return CheckResult("Projects API", False, str(e)[:120], "Ensure ALLOW_ANONYMOUS_DEV=1 for local dev")


def check_deployments(api_base: Optional[str] = None, project_id: Optional[str] = None) -> CheckResult:
    import json

    base = api_base or resolve_api_base()[0]
    pid = project_id or os.environ.get("DEFAULT_PROJECT_UUID", "00000000-0000-4000-8000-000000000002")
    try:
        req = Request(
            f"{base}/deployments",
            headers={
                "User-Agent": "agent-cloud-dev-doctor/1.0",
                "Content-Type": "application/json",
                "X-Project-ID": pid,
            },
        )
        with urlopen(req, timeout=5.0) as resp:
            body = json.loads(resp.read().decode())
        deps = body.get("deployments") or []
        active = [d for d in deps if d.get("status") == "active"]
        if active:
            return CheckResult("Sample deployment", True, f"{len(active)} active (e.g. {active[0].get('agent_name')})")
        if deps:
            return CheckResult("Sample deployment", True, f"{len(deps)} deployment(s), none active")
        return CheckResult(
            "Sample deployment",
            False,
            "none yet",
            "Deploy: Dashboard → Deployments → Deploy sample echo agent",
        )
    except Exception as e:
        return CheckResult("Sample deployment", False, str(e)[:120])


def run_preflight_checks(*, include_deep: bool = False) -> List[CheckResult]:
    api_base, _ = resolve_api_base()
    results = [
        check_postgres_direct(),
        check_redis_direct(),
        check_api(api_base),
    ]
    if include_deep:
        results.append(check_api_deep(api_base))
    results.extend(
        [
            check_dashboard(),
            check_workers(),
            check_projects(api_base),
            check_deployments(api_base),
        ]
    )
    return results


def print_report(results: List[CheckResult], stale: Optional[StaleReport] = None) -> bool:
    print("")
    print("Agent Cloud — dev doctor")
    print("=" * 50)
    all_ok = True
    for r in results:
        print(r.line())
        if not r.passed:
            all_ok = False
            if r.hint:
                print(f"         -> {r.hint}")
    if stale and stale.warnings:
        print("")
        print("  [WARN] Stale / conflicting processes")
        all_ok = False
        for w in stale.warnings:
            print(f"         • {w}")
        if stale.recovery_commands:
            print("         Recovery:")
            for cmd in stale.recovery_commands:
                print(f"           {cmd}")
    print("=" * 50)
    if all_ok:
        print("  OVERALL: PASS - local stack looks healthy")
    else:
        print("  OVERALL: FAIL - fix items above before alpha testing")
    print("")
    return all_ok
