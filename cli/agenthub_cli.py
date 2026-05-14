#!/usr/bin/env python3
"""
Developer CLI for creating, validating, and publishing agent packages.

Usage:
  agenthub init-agent <name>
  agenthub validate <path>
  agenthub publish <path> [--api-url URL]
  agenthub run <agent> <task> [--api-url URL]
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from pathlib import Path

# Add project root so sdk/package_spec and sdk/package_loader can be imported when run as script.
_CLI_DIR = Path(__file__).resolve().parent
_ROOT = _CLI_DIR.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _agent_yaml_template(name: str) -> str:
    return f"""name: {name}
version: v1
description: Example agent
capabilities:
  - custom
entrypoint: agent.py
"""


def _agent_py_template(name: str) -> str:
    safe_name = name.replace("-", "_").replace(" ", "_")
    class_name = "".join(w.title() for w in safe_name.split("_"))
    if not class_name.endswith("Agent"):
        class_name += "Agent"
    return f'''"""
Agent: {name}
"""

from sdk.agent import Agent


class {class_name}(Agent):
    name = "{name}"
    description = "Example agent"
    capabilities = ["custom"]
    tools = []

    def run(self, state):
        task = state.get("task", "")
        return {{"result": f"Processed: {{task}}"}}
'''


def _requirements_txt_template() -> str:
    return """# Add dependencies for your agent, e.g.:
# requests>=2.28.0
"""


def cmd_init_agent(name: str) -> int:
    """Create folder structure: <name>/agent.yaml, agent.py, requirements.txt."""
    if not name or not name.strip():
        print("Error: agent name is required", file=sys.stderr)
        return 1
    name = name.strip()
    dir_path = Path(name)
    if dir_path.exists():
        print(f"Error: {dir_path} already exists", file=sys.stderr)
        return 1
    dir_path.mkdir(parents=True)
    (dir_path / "agent.yaml").write_text(_agent_yaml_template(name), encoding="utf-8")
    (dir_path / "agent.py").write_text(_agent_py_template(name), encoding="utf-8")
    (dir_path / "requirements.txt").write_text(_requirements_txt_template(), encoding="utf-8")
    print(f"Created agent package: {dir_path}/")
    print("  agent.yaml")
    print("  agent.py")
    print("  requirements.txt")
    return 0


def cmd_validate(path: str) -> int:
    """Check agent.yaml exists, entrypoint exists, Agent class present."""
    pkg_dir = Path(path).resolve()
    if not pkg_dir.is_dir():
        print(f"Error: not a directory: {pkg_dir}", file=sys.stderr)
        return 1
    errors = []
    spec = None
    # agent.yaml
    yaml_path = pkg_dir / "agent.yaml"
    if not yaml_path.is_file():
        errors.append("agent.yaml not found")
    else:
        try:
            from sdk.package_spec import load_spec
            spec = load_spec(pkg_dir)
        except Exception as e:
            errors.append(f"agent.yaml invalid: {e}")
            spec = None
    if spec:
        entrypoint = spec.get("entrypoint") or "agent.py"
        entry_path = pkg_dir / entrypoint
        if not entry_path.is_file():
            errors.append(f"entrypoint not found: {entrypoint}")
        else:
            try:
                import importlib.util
                mod_name = f"_validate_{pkg_dir.name}"
                spec_mod = importlib.util.spec_from_file_location(mod_name, entry_path)
                if spec_mod and spec_mod.loader:
                    mod = importlib.util.module_from_spec(spec_mod)
                    spec_mod.loader.exec_module(mod)
                    from sdk.agent import Agent
                    found = False
                    for attr in dir(mod):
                        obj = getattr(mod, attr)
                        if isinstance(obj, type) and issubclass(obj, Agent) and obj is not Agent:
                            found = True
                            break
                    if not found:
                        errors.append("No Agent subclass found in entrypoint")
            except Exception as e:
                errors.append(f"entrypoint load error: {e}")
    if errors:
        for e in errors:
            print(f"Error: {e}", file=sys.stderr)
        return 1
    print("Valid: agent.yaml, entrypoint, and Agent class OK.")
    return 0


def cmd_publish(path: str, api_url: str, token: str | None = None) -> int:
    """Publish agent: 1) validate package 2) register via developer economy (POST /developers/agents + versions) or legacy POST /agents/publish."""
    try:
        import requests
    except ImportError:
        print("Error: requests is required. Install with: pip install requests", file=sys.stderr)
        return 1
    pkg_dir = Path(path).resolve()
    if not pkg_dir.is_dir():
        print(f"Error: not a directory: {pkg_dir}", file=sys.stderr)
        return 1
    try:
        from sdk.package_spec import load_spec
        spec = load_spec(pkg_dir)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    api_base = api_url.rstrip("/")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Prefer developer economy API when token is provided: one-step publish via /developers/agents/publish
    if token:
        agent_name = (spec.get("name") or "agent").strip().lower().replace(" ", "_")
        metadata = {
            "agent_name": agent_name,
            "description": spec.get("description") or "No description",
            "category": (spec.get("capabilities") or ["custom"])[0] if spec.get("capabilities") else "custom",
            "price_per_run": float(spec.get("price") or 0),
            "currency": "USD",
        }
        try:
            # Ensure agent exists (for name ownership); if it already exists, publish will reuse it
            r = requests.post(f"{api_base}/developers/agents", json=metadata, headers=headers, timeout=30)
            if r.status_code == 400 and "already taken" in (r.json().get("detail") or ""):
                r2 = requests.get(f"{api_base}/developers/my-agents", headers=headers, timeout=30)
                r2.raise_for_status()
                agents = r2.json().get("agents") or []
                agent = next((a for a in agents if (a.get("agent_name") or "").lower() == agent_name), None)
                if not agent:
                    print(r.json().get("detail", "Agent name taken"), file=sys.stderr)
                    return 1
                agent_id = agent["agent_id"]
            else:
                r.raise_for_status()
                data = r.json()
                agent_id = data.get("agent", {}).get("agent_id")
                if not agent_id:
                    print("Unexpected response: no agent_id", file=sys.stderr)
                    return 1
            version = (spec.get("version") or "1.0.0").strip()
            changelog = (spec.get("changelog") or "").strip()
            # Zip package directory
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for f in pkg_dir.rglob("*"):
                    if f.is_file() and not f.name.startswith("."):
                        arcname = f.relative_to(pkg_dir)
                        zf.write(f, arcname)
            buf.seek(0)
            upload_headers = {"Authorization": headers["Authorization"]} if token else {}
            r3 = requests.post(
                f"{api_base}/developers/agents/publish",
                files={"file": ("package.zip", buf.getvalue(), "application/zip")},
                data={
                    "metadata": json.dumps(metadata),
                    "version": version,
                    "changelog": changelog,
                },
                headers=upload_headers,
                timeout=60,
            )
            r3.raise_for_status()
            print(f"Published: {agent_name} v{version} (developer economy, submitted for review).")
            return 0
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}", file=sys.stderr)
            if hasattr(e, "response") and e.response is not None and e.response.text:
                print(e.response.text, file=sys.stderr)
            return 1

    # Legacy: POST /agents/publish (no auth)
    url = f"{api_base}/agents/publish"
    payload = {
        "name": spec["name"],
        "description": spec.get("description") or "No description",
        "version": spec.get("version") or "v1",
        "capabilities": spec.get("capabilities") or [],
        "author": spec.get("author") or "unknown",
        "price": float(spec.get("price") or 0),
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        print(f"Published: {data.get('agent', {}).get('name', spec['name'])}")
        return 0
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response is not None and e.response.text:
            print(e.response.text, file=sys.stderr)
        return 1


def cmd_run(agent: str, task: str, api_url: str) -> int:
    """Call POST /agents/run."""
    try:
        import requests
    except ImportError:
        print("Error: requests is required. Install with: pip install requests", file=sys.stderr)
        return 1
    url = f"{api_url.rstrip('/')}/agents/run"
    payload = {"agent": agent, "task": task}
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        print(f"Task queued. Agent: {data.get('agent', agent)}")
        return 0
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response is not None and e.response.text:
            print(e.response.text, file=sys.stderr)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="agenthub", description="Agent package developer CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init-agent", help="Create a new agent package")
    p_init.add_argument("name", help="Agent name (folder and agent name)")
    p_init.set_defaults(func=lambda a: cmd_init_agent(a.name))

    p_validate = sub.add_parser("validate", help="Validate an agent package")
    p_validate.add_argument("path", help="Path to package directory")
    p_validate.set_defaults(func=lambda a: cmd_validate(a.path))

    p_publish = sub.add_parser("publish", help="Publish package (developer economy with --token, else legacy)")
    p_publish.add_argument("path", help="Path to package directory (e.g. ./agents/competitor_monitor)")
    p_publish.add_argument("--api-url", default="http://127.0.0.1:8000", help="API base URL")
    p_publish.add_argument("--token", default=None, help="Bearer token (for developer economy: register + agents + version)")
    p_publish.set_defaults(func=lambda a: cmd_publish(a.path, a.api_url, a.token or __import__("os").environ.get("AGENT_CLI_TOKEN")))

    p_run = sub.add_parser("run", help="Run an agent (POST /agents/run)")
    p_run.add_argument("agent", help="Agent name")
    p_run.add_argument("task", help="Task text")
    p_run.add_argument("--api-url", default="http://127.0.0.1:8000", help="API base URL")
    p_run.set_defaults(func=lambda a: cmd_run(a.agent, a.task, a.api_url))

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
