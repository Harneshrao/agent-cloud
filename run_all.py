#!/usr/bin/env python3
"""
Run the full Agent Cloud platform with one command.

Starts in order:
  1. API (uvicorn)          → http://localhost:8000 — we wait until it is ready
  2. Worker                 → processes tasks
  3. Scheduler              → assigns tasks
  4. Dashboard (Next.js)     → http://localhost:3000 (only after API is ready)

Usage (from project root):
  py -3.11 run_all.py
  or (if .venv is Python 3.11):  python run_all.py

Required Python version: 3.11 (3.14 causes crashes with uvicorn/multiprocessing).

Before first run, install dashboard deps once:
  cd dashboard && npm install && cd ..

Stop everything with Ctrl+C once; all child processes will be terminated.
"""

import atexit
import os
import signal
import subprocess
import sys
import time

try:
    import requests
except ImportError:
    requests = None


def wait_for_api(timeout: int = 60) -> tuple[str, int]:
    """Block until the API responds with 200 on 8000 or 8001. Returns (base_url, port)."""
    print("Waiting for API to become ready...")
    start = time.time()
    while time.time() - start < timeout:
        for port in (8000, 8001):
            try:
                r = requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
                if r.status_code == 200:
                    base = f"http://127.0.0.1:{port}"
                    print(f"API is ready at {base}.")
                    return (base, port)
            except Exception:
                pass
        time.sleep(1)
    raise RuntimeError("API did not start within timeout")

required_major, required_minor = 3, 11
if sys.version_info.major != required_major or sys.version_info.minor != required_minor:
    print("ERROR: Agent Cloud must run with Python 3.11")
    print(f"Current version: {sys.version}")
    print("Please run using:")
    print("  py -3.11 run_all.py")
    sys.exit(1)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_DIR = os.path.join(PROJECT_ROOT, "dashboard")

# Use Python 3.11 for all Python child processes
if sys.platform == "win32":
    PYTHON_CMD = ["py", "-3.11"]
else:
    VENV_PYTHON = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")
    PYTHON_CMD = [VENV_PYTHON] if os.path.isfile(VENV_PYTHON) else [sys.executable]

processes = []


def kill_all():
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                p.kill()
            except ProcessLookupError:
                pass
    processes.clear()


def start(cmd, cwd=None, env=None, shell=False, description=""):
    """Start a subprocess; output is inherited so you see all logs in one terminal."""
    cwd = cwd or PROJECT_ROOT
    env = env or os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("ALLOW_ANONYMOUS_DEV", "1")  # so dashboard can call API without login
    if sys.platform == "win32" and ("npm" in str(cmd) or "node" in str(cmd)):
        full_cmd = " ".join(cmd) if isinstance(cmd, (list, tuple)) else cmd
        p = subprocess.Popen(full_cmd, cwd=cwd, env=env, shell=True)
    else:
        p = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            shell=shell,
            stdout=None,
            stderr=None,
        )
    processes.append(p)
    print(f"[run_all] Started {description or str(cmd)} (PID {p.pid})")
    return p


def main():
    if requests is None:
        print("ERROR: run_all.py requires 'requests'. Install with: pip install -r requirements.txt")
        sys.exit(1)

    from run_backend import apply_skip_migration_if_no_alembic, require_sqlalchemy_or_exit

    apply_skip_migration_if_no_alembic()
    require_sqlalchemy_or_exit()

    atexit.register(kill_all)

    def handler(_signum, _frame):
        print("\n[run_all] Shutting down all processes...")
        kill_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, handler)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, handler)

    print("=" * 60)
    print("Agent Cloud — starting API, Worker, Scheduler, Dashboard")
    print("=" * 60)

    # 1. Start API (on Windows run_backend.py uses --no-reload by default and may bind to 8001 if 8000 is in use)
    print("Starting API...")
    # Always use run_backend.py so SQLAlchemy / migration env checks match Windows
    api_cmd = PYTHON_CMD + [os.path.join(PROJECT_ROOT, "run_backend.py")]
    if sys.platform == "win32":
        api_cmd = ["py", "-3.11", "run_backend.py"]
    start(api_cmd, description="API (http://localhost:8000 or 8001)")

    # Wait for API to be ready (tries 8000 then 8001)
    api_base, api_port = wait_for_api(timeout=60)

    # 2. Worker
    print("Starting Worker...")
    start(
        PYTHON_CMD + ["-m", "workers.worker"],
        description="Worker",
    )
    time.sleep(0.5)

    # 3. Scheduler
    print("Starting Scheduler...")
    start(
        PYTHON_CMD + ["start_scheduler.py"],
        description="Scheduler",
    )
    time.sleep(0.5)

    # 4. Dashboard — only after API is ready (set API_UPSTREAM if API is on 8001)
    print("Starting Dashboard...")
    dash_env = os.environ.copy()
    dash_env.setdefault("PYTHONUNBUFFERED", "1")
    dash_env.setdefault("ALLOW_ANONYMOUS_DEV", "1")
    if api_port != 8000:
        dash_env["API_UPSTREAM"] = api_base
    start(
        ["npm", "run", "dev"],
        cwd=DASHBOARD_DIR,
        env=dash_env,
        description="Dashboard (http://localhost:3000)",
    )

    print()
    print("All services started.")
    print(f"  API:       {api_base}")
    print(f"  API Docs:  {api_base}/docs")
    print("  Dashboard: http://localhost:3000")
    print()
    print("Press Ctrl+C to stop all.")
    print("=" * 60)

    try:
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        pass
    finally:
        kill_all()


if __name__ == "__main__":
    main()
