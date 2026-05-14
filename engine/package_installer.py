"""
Install an automation package into a project: create workflow template, version, and template install.

Reuses workflow_templates, template_versions, template_installs. Does not modify workers or task queue.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from database import template_installs
from database import template_versions
from database import workflow_templates
from database.package_stats import increment_package_install
from registry.package_registry import package_registry


def _parameters_to_input_schema(parameters: Any) -> Optional[Dict[str, Any]]:
    """Convert template.yaml parameters (e.g. { topic: string, region: string }) to JSON Schema."""
    if not isinstance(parameters, dict):
        return None
    props = {}
    for key, val in parameters.items():
        if isinstance(val, str):
            type_ = "string" if val.strip().lower() in ("string", "str", "text") else "string"
        elif isinstance(val, dict) and "type" in val:
            type_ = val["type"]
        else:
            type_ = "string"
        props[key] = {"type": type_}
    return {"type": "object", "properties": props, "required": list(props.keys()) if props else []}


def install_package(
    project_id: int,
    package_name: str,
    author_user_id: int,
) -> Dict[str, Any]:
    """
    Install an automation package into a project.
    1. Load package metadata from package_registry
    2. Create workflow template (name, description, dag_definition, input_schema)
    3. Create template version with package version
    4. Install template into project via template_installs.install
    """
    pkg = package_registry.get_package(package_name)
    if pkg is None:
        raise ValueError(f"Package not found: {package_name}")

    name = pkg.get("name") or package_name
    version = str(pkg.get("version") or "1.0")
    description = str(pkg.get("description") or "")
    dag_definition = pkg.get("dag_definition")
    if not isinstance(dag_definition, dict):
        dag_definition = pkg.get("workflow") or {}
    if isinstance(dag_definition, dict) and "nodes" not in dag_definition:
        dag_definition = {"nodes": []}
    input_schema = pkg.get("input_schema")
    if input_schema is None:
        input_schema = _parameters_to_input_schema(pkg.get("parameters"))

    template = workflow_templates.create_template(
        name=name,
        description=description,
        author_user_id=author_user_id,
        dag_definition=dag_definition,
        input_schema=input_schema,
        visibility="private",
        forked_from_template_id=None,
    )
    template_id = template["id"]
    try:
        template_versions.create_version(
            template_id=template_id,
            version=version,
            dag_definition=dag_definition,
        )
    except ValueError:
        pass  # version already exists
    install = template_installs.install(template_id=template_id, project_id=project_id, config=None)
    try:
        increment_package_install(package_name)
    except Exception:
        pass
    return {
        "status": "installed",
        "template_id": template_id,
        "project_id": project_id,
        "package_name": package_name,
        "version": version,
        "install_id": install.get("id"),
    }
