"""
Automation package loader: scan automation_packages/, read template.yaml,
register packages and load agents into agent_registry.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from registry.agent_registry import agent_registry
from registry.package_registry import package_registry

from automation_packages.prompt_loader import load_prompts_for_package

try:
    from database.automation_packages_db import upsert_package as _db_upsert_package
except Exception:
    _db_upsert_package = None


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _workflow_to_dag_definition(
    workflow: Any,
    parameters: Optional[Dict[str, Any]] = None,
    namespace: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convert template.yaml workflow to dag_definition format expected by template_runner.
    workflow can be: { "nodes": [ "agent1", "agent2" ] } or { "nodes": [ {"id": "n1", "agent": "a1", "task": "..."}, ... ] }.
    If namespace is set (e.g. package name), node ids and agent names are namespaced as namespace.agent_name
    so workflows reference the correct package agents and do not collide across packages.
    """
    if not isinstance(workflow, dict):
        return {"nodes": []}
    nodes_raw = workflow.get("nodes") or []
    nodes_out: List[Dict[str, Any]] = []
    for i, n in enumerate(nodes_raw):
        if isinstance(n, str):
            node_id = n
            agent_name = n
            deps = [nodes_out[-1]["id"]] if nodes_out else []
        elif isinstance(n, dict):
            node_id = n.get("id") or n.get("agent") or str(i)
            agent_name = n.get("agent") or node_id
            deps = n.get("deps") if isinstance(n.get("deps"), list) else ([nodes_out[-1]["id"]] if nodes_out else [])
        else:
            continue
        task = n.get("task", "") if isinstance(n, dict) else ""
        if namespace:
            node_id = f"{namespace}.{node_id}"
            agent_name = f"{namespace}.{agent_name}"
            deps = [f"{namespace}.{d}" for d in deps]
        nodes_out.append({
            "id": node_id,
            "agent": agent_name,
            "task": task,
            "deps": deps,
        })
    params = parameters if isinstance(parameters, dict) else None
    return {"nodes": nodes_out, "parameters": params}


def _load_agent_module(module_name: str, file_path: Path) -> Any:
    """Load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    if module_name in sys.modules:
        return sys.modules[module_name]
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _find_agent_class(module: Any):
    """Return the first Agent subclass in the module."""
    try:
        from sdk.agent import Agent
    except ImportError:
        return None
    for attr_name in dir(module):
        obj = getattr(module, attr_name)
        if (
            isinstance(obj, type)
            and issubclass(obj, Agent)
            and obj is not Agent
        ):
            return obj
    return None


def _load_agents_from_package(package_path: Path, namespace: str) -> List[str]:
    """
    Load agent modules from package_path/agents/*.py and register with agent_registry
    using namespaced names: namespace.agent_name. Returns list of namespaced agent names.
    """
    agents_dir = package_path / "agents"
    if not agents_dir.is_dir():
        return []
    registered: List[str] = []
    safe_ns = namespace.replace("-", "_")
    for py_file in sorted(agents_dir.glob("*.py")):
        if py_file.name.startswith("_"):
            continue
        try:
            mod_name = f"automation_pkg_{safe_ns}_{py_file.stem}_{id(package_path)}"
            mod = _load_agent_module(mod_name, py_file)
            agent_cls = _find_agent_class(mod)
            if agent_cls is None:
                continue
            agent = agent_cls()
            original_name = getattr(agent, "name", None) or py_file.stem
            if not original_name:
                continue
            namespaced_name = f"{namespace}.{original_name}"
            agent.name = namespaced_name
            agent_registry.register_agent(agent)
            registered.append(namespaced_name)
        except Exception:
            continue
    return registered


def load_package(package_path: Path) -> Dict[str, Any]:
    """
    Load one automation package from a directory.
    1. Read template.yaml
    2. Build dag_definition from workflow
    3. Register package in package_registry
    4. Load agents from agents/ and register in agent_registry
    """
    package_path = package_path.resolve()
    template_yaml = package_path / "template.yaml"
    if not template_yaml.is_file():
        raise FileNotFoundError(f"template.yaml not found in {package_path}")

    data = _load_yaml(template_yaml)
    name = (data.get("name") or package_path.name).strip()
    if not name:
        name = package_path.name
    namespace = package_path.name
    version = str(data.get("version") or "1.0")
    description = str(data.get("description") or "")
    agents_list = data.get("agents")
    if isinstance(agents_list, list):
        agents_list = [str(a) for a in agents_list]
    else:
        agents_list = []
    workflow = data.get("workflow")
    parameters = data.get("parameters")
    dag_definition = _workflow_to_dag_definition(workflow, parameters, namespace=namespace)
    input_schema = parameters if isinstance(parameters, dict) else None

    # Load agent modules and register with namespaced names (namespace.agent_name)
    loaded_agents = _load_agents_from_package(package_path, namespace)
    # Load prompts from prompts/ and register with namespaced names (namespace.prompt_name)
    load_prompts_for_package(package_path, namespace)

    metadata = {
        "name": name,
        "version": version,
        "namespace": namespace,
        "description": description,
        "agents": agents_list or [a.split(".", 1)[-1] for a in loaded_agents],
        "workflow": workflow,
        "dag_definition": dag_definition,
        "input_schema": input_schema,
        "parameters": parameters,
        "path": str(package_path),
    }
    package_registry.register_package(name, metadata)
    if _db_upsert_package is not None:
        try:
            _db_upsert_package(name=name, version=version, description=description)
        except Exception:
            pass
    return metadata


def load_all_packages() -> List[Dict[str, Any]]:
    """
    Scan automation_packages/ and load every package (directories containing template.yaml).
    Call during platform startup. Returns list of loaded package metadata.
    """
    root = _project_root()
    packages_dir = root / "automation_packages"
    if not packages_dir.is_dir():
        return []
    loaded = []
    for item in sorted(packages_dir.iterdir()):
        if not item.is_dir():
            continue
        template_yaml = item / "template.yaml"
        if not template_yaml.is_file():
            continue
        try:
            meta = load_package(item)
            loaded.append(meta)
        except Exception:
            continue
    return loaded
