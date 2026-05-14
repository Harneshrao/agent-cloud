"""
Sandbox execution engine: run agents inside isolated Docker containers.

Uses a container pool for reuse (engine/container_pool.py) to reduce
latency: acquire container, copy agent package and run script, exec,
then release container back to the pool.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from engine.container_pool import get_pool

# Default image when starting new containers (pool or one-shot fallback).
SANDBOX_IMAGE = os.environ.get("AGENT_SANDBOX_IMAGE", "agent-runtime:latest")
# Timeout in seconds for a single agent run inside a container.
SANDBOX_TIMEOUT = int(os.environ.get("AGENT_SANDBOX_TIMEOUT", "120"))
# Timeout in seconds to wait for a container from the pool.
POOL_ACQUIRE_TIMEOUT = int(os.environ.get("SANDBOX_POOL_ACQUIRE_TIMEOUT", "60"))

# In-container script: load agent from /app/agent, run with task_input, print JSON result.
_RUNNER_SCRIPT = r"""
import json
import os
import sys
from pathlib import Path

def main():
    platform = Path("/app/platform")
    agent_dir = Path("/app/agent")
    if not platform.is_dir() or not agent_dir.is_dir():
        print(json.dumps({"status": "error", "error": "Mounts missing: /app/platform, /app/agent"}))
        return 1

    sys.path.insert(0, str(platform))

    task_json = os.environ.get("TASK_JSON", "{}")
    try:
        task_input = json.loads(task_json) if task_json else {}
    except json.JSONDecodeError as e:
        print(json.dumps({"status": "error", "error": f"Invalid TASK_JSON: {e}"}))
        return 1

    try:
        from sdk.package_spec import load_spec
        from sdk.agent import Agent
    except ImportError as e:
        print(json.dumps({"status": "error", "error": f"Platform imports failed: {e}"}))
        return 1

    try:
        spec = load_spec(agent_dir)
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"Failed to load agent spec: {e}"}))
        return 1

    entrypoint = spec.get("entrypoint", "agent.py")
    entry_path = agent_dir / entrypoint
    if not entry_path.is_file():
        print(json.dumps({"status": "error", "error": f"Entrypoint not found: {entrypoint}"}))
        return 1

    import importlib.util
    spec_mod = importlib.util.spec_from_file_location("agent_module", entry_path)
    if spec_mod is None or spec_mod.loader is None:
        print(json.dumps({"status": "error", "error": "Could not load entrypoint module"}))
        return 1
    mod = importlib.util.module_from_spec(spec_mod)
    sys.modules["agent_module"] = mod
    spec_mod.loader.exec_module(mod)

    agent_cls = None
    for name in dir(mod):
        obj = getattr(mod, name)
        if (
            isinstance(obj, type)
            and issubclass(obj, Agent)
            and obj is not Agent
        ):
            agent_cls = obj
            break
    if agent_cls is None:
        print(json.dumps({"status": "error", "error": "No Agent subclass found in entrypoint"}))
        return 1

    state = task_input if isinstance(task_input, dict) else {"task": task_input}
    try:
        agent = agent_cls()
        result = agent.run(state)
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        return 1

    def enc(o):
        if o is None or isinstance(o, (bool, int, float, str)):
            return o
        if isinstance(o, dict):
            return {k: enc(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [enc(x) for x in o]
        return str(o)

    out = enc(result)
    print(json.dumps({"status": "success", "output": out}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""


def _run_in_container(
    container_id: str,
    package_path: Path,
    platform_root: Path,
    task_json: str,
) -> tuple[str, str, int]:
    """
    Copy agent package and runner into container, exec the runner.
    Returns (stdout, stderr, returncode).
    """
    with tempfile.TemporaryDirectory(prefix="agent_sandbox_") as tmp:
        runner_path = Path(tmp) / "run_agent_in_sandbox.py"
        runner_path.write_text(_RUNNER_SCRIPT, encoding="utf-8")

        # Ensure target dirs exist and copy agent package and runner script.
        subprocess.run(
            ["docker", "exec", container_id, "sh", "-c", "mkdir -p /app/agent /runner"],
            capture_output=True,
            timeout=10,
            cwd=str(platform_root),
            check=False,
        )
        subprocess.run(
            ["docker", "cp", f"{package_path}/.", f"{container_id}:/app/agent/"],
            capture_output=True,
            timeout=30,
            cwd=str(platform_root),
            check=False,
        )
        subprocess.run(
            ["docker", "cp", str(runner_path), f"{container_id}:/runner/run_agent_in_sandbox.py"],
            capture_output=True,
            timeout=10,
            cwd=str(platform_root),
            check=False,
        )

        proc = subprocess.run(
            [
                "docker", "exec",
                "-e", f"TASK_JSON={task_json}",
                "-e", "PYTHONPATH=/app/platform",
                container_id,
                "sh", "-c", "pip install -q pyyaml && exec python /runner/run_agent_in_sandbox.py",
            ],
            capture_output=True,
            text=True,
            timeout=SANDBOX_TIMEOUT,
            cwd=str(platform_root),
        )
        return (proc.stdout or "", proc.stderr or "", proc.returncode)


def _run_one_shot(
    package_path: Path,
    platform_root: Path,
    task_json: str,
) -> dict[str, Any]:
    """Fallback: run agent in a new container (no pool). Same behavior as original run_agent."""
    with tempfile.TemporaryDirectory(prefix="agent_sandbox_") as tmp:
        runner_path = Path(tmp) / "run_agent_in_sandbox.py"
        runner_path.write_text(_RUNNER_SCRIPT, encoding="utf-8")
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{platform_root}:/app/platform:ro",
            "-v", f"{package_path}:/app/agent:ro",
            "-v", f"{tmp}:/runner:ro",
            "-e", f"TASK_JSON={task_json}",
            "-e", "PYTHONPATH=/app/platform",
            "--network", "none",
            "-e", "PYTHONDONTWRITEBYTECODE=1",
            "--memory=256m",
            "--cpus=0.5",
            SANDBOX_IMAGE,
            "sh", "-c", "pip install -q pyyaml && exec python /runner/run_agent_in_sandbox.py",
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=SANDBOX_TIMEOUT,
                cwd=str(platform_root),
            )
        except subprocess.TimeoutExpired:
            return {"status": "error", "error": f"Sandbox timed out after {SANDBOX_TIMEOUT}s", "output": None}
        except FileNotFoundError:
            return {"status": "error", "error": "Docker not found; ensure Docker is installed and on PATH", "output": None}
        except Exception as e:
            return {"status": "error", "error": str(e), "output": None}
        return _parse_output(proc.stdout or "", proc.stderr or "", proc.returncode)


def _parse_output(out: str, err: str, returncode: int) -> dict[str, Any]:
    """Parse runner stdout/stderr into the standard result dict."""
    lines = [ln.strip() for ln in out.strip().splitlines() if ln.strip()]
    if lines:
        try:
            last = json.loads(lines[-1])
            if last.get("status") == "success":
                return {"status": "success", "output": last.get("output")}
            return {"status": "error", "error": last.get("error", "Unknown error"), "output": last.get("output")}
        except json.JSONDecodeError:
            pass
    return {
        "status": "error",
        "error": err.strip() or out.strip() or f"Container exited with code {returncode}",
        "output": None,
    }


def run_agent(package_path: str | Path, task_input: dict[str, Any] | Any) -> dict[str, Any]:
    """
    Run an agent package inside an isolated Docker container.

    Uses the container pool: acquire a container, copy the agent package and
    runner script into it, exec the runner, then release the container.
    If no pool container is available within the acquire timeout, falls back
    to a one-shot container run.

    Args:
        package_path: Path to the agent package directory (must contain agent.yaml and entrypoint).
        task_input: State dict (or value) passed to the agent's run(state).

    Returns:
        {"status": "success", "output": <agent run result>}
        or {"status": "error", "error": "<message>"} (and optionally "output": None).
    """
    package_path = Path(package_path).resolve()
    if not package_path.is_dir():
        return {"status": "error", "error": f"Package path is not a directory: {package_path}", "output": None}

    platform_root = Path(__file__).resolve().parent.parent
    if not (platform_root / "sdk").is_dir():
        return {"status": "error", "error": f"Platform root missing sdk: {platform_root}", "output": None}

    task_json = json.dumps(task_input, default=str)
    pool = get_pool()
    container_id = pool.acquire_container(timeout=POOL_ACQUIRE_TIMEOUT)

    if container_id is None:
        return _run_one_shot(package_path, platform_root, task_json)

    try:
        out, err, returncode = _run_in_container(
            container_id, package_path, platform_root, task_json
        )
        return _parse_output(out, err, returncode)
    except subprocess.TimeoutExpired:
        return {"status": "error", "error": f"Sandbox timed out after {SANDBOX_TIMEOUT}s", "output": None}
    except FileNotFoundError:
        return {"status": "error", "error": "Docker not found; ensure Docker is installed and on PATH", "output": None}
    except Exception as e:
        return {"status": "error", "error": str(e), "output": None}
    finally:
        pool.release_container(container_id)
