"""
User Agent Execution: installations of marketplace agents per project.

Table: agent_installations
  installation_id (PK), project_id, agent_name, configuration (JSON), installed_at, status

Enables: install from marketplace, configure inputs, run or schedule, view results.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db import db


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def _defaults_from_schema(input_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Build default configuration from agent input_schema. Schema keys are param names; value can be { type, default } or a simple default."""
    if not input_schema:
        return {}
    out: Dict[str, Any] = {}
    for key, val in input_schema.items():
        if isinstance(val, dict) and "default" in val:
            out[key] = val["default"]
        elif not isinstance(val, dict):
            out[key] = val
    return out


def get_agent_input_schema(agent_name: str) -> Dict[str, Any]:
    """Return input_schema for agent from registry (optional class attribute)."""
    try:
        from registry.agent_registry import agent_registry
        agent = agent_registry.get_agent(agent_name)
        if agent is None:
            return {}
        return getattr(agent, "input_schema", None) or {}
    except Exception:
        return {}


def install_agent(project_id: int, agent_name: str) -> Dict[str, Any]:
    """
    Validate agent exists (in registry or as published agent with code), create installation record,
    initialize configuration from agent input_schema defaults. Returns the installation record.
    """
    from registry.agent_registry import agent_registry
    from database.developer_economy import get_published_agent_by_name, get_latest_version
    if agent_registry.get_agent(agent_name) is not None:
        pass  # built-in agent
    else:
        pub = get_published_agent_by_name(agent_name)
        if not pub:
            raise ValueError(f"Agent '{agent_name}' is not registered")
        ver = get_latest_version(pub["agent_id"])
        if not ver or not (ver.get("code_location") or "").strip():
            raise ValueError(f"Agent '{agent_name}' has no deployed package; upload a version first")
    _ensure_schema()
    input_schema = get_agent_input_schema(agent_name)
    configuration = _defaults_from_schema(input_schema)
    config_json = json.dumps(configuration)
    conn = db.get_connection()
    cur = conn.cursor()
    now = datetime.utcnow()
    cur.execute(
        """
        INSERT INTO agent_installations (project_id, agent_name, configuration, installed_at, status)
        VALUES (?, ?, ?, ?, 'active')
        """,
        (project_id, agent_name, config_json, now),
    )
    conn.commit()
    installation_id = int(cur.lastrowid)
    try:
        from database.agent_installs import record_install
        record_install(agent_name, project_id)
    except Exception:
        pass
    try:
        from database.developer_economy import get_published_agent_by_name, record_install_for_agent
        pub = get_published_agent_by_name(agent_name)
        if pub:
            record_install_for_agent(pub["agent_id"])
    except Exception:
        pass
    return get_installation(installation_id)


def get_installation(installation_id: int) -> Optional[Dict[str, Any]]:
    """Return installation by id. configuration is parsed to dict."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT installation_id, project_id, agent_name, configuration, installed_at, status
        FROM agent_installations WHERE installation_id = ?
        """,
        (installation_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    config = row["configuration"]
    if isinstance(config, str) and config:
        try:
            config = json.loads(config)
        except (json.JSONDecodeError, TypeError):
            config = {}
    elif config is None:
        config = {}
    installed_at = row["installed_at"]
    if hasattr(installed_at, "isoformat"):
        installed_at = installed_at.isoformat()
    return {
        "installation_id": row["installation_id"],
        "project_id": row["project_id"],
        "agent_name": row["agent_name"],
        "configuration": config,
        "installed_at": installed_at,
        "status": row["status"],
    }


def list_installations_by_project(project_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """List installations for a project, optionally filtered by status."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    if status:
        cur.execute(
            """
            SELECT installation_id, project_id, agent_name, configuration, installed_at, status
            FROM agent_installations WHERE project_id = ? AND status = ?
            ORDER BY installed_at DESC
            """,
            (project_id, status),
        )
    else:
        cur.execute(
            """
            SELECT installation_id, project_id, agent_name, configuration, installed_at, status
            FROM agent_installations WHERE project_id = ?
            ORDER BY installed_at DESC
            """,
            (project_id,),
        )
    out = []
    for row in cur.fetchall():
        r = get_installation(row["installation_id"])
        if r:
            out.append(r)
    return out


def update_agent_configuration(installation_id: int, configuration: Dict[str, Any]) -> bool:
    """
    Update configuration for an installation. Caller should validate against input_schema
    before calling; this only persists. Returns True if updated.
    """
    _ensure_schema()
    inst = get_installation(installation_id)
    if inst is None:
        return False
    config_json = json.dumps(configuration)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_installations SET configuration = ? WHERE installation_id = ?",
        (config_json, installation_id),
    )
    conn.commit()
    return cur.rowcount > 0


def set_installation_status(installation_id: int, status: str) -> bool:
    """Update lifecycle status (`active`, `suspended`, `rolled_back`). Returns True if a row changed."""
    allowed = frozenset({"active", "suspended", "rolled_back", "pending"})
    if status not in allowed:
        raise ValueError(f"invalid status: {status}")
    _ensure_schema()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE agent_installations SET status = ? WHERE installation_id = ?",
        (status, installation_id),
    )
    conn.commit()
    return cur.rowcount > 0


def validate_configuration(agent_name: str, configuration: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate configuration against agent input_schema. Return (valid, error_message).
    Required parameters (no default in schema) must be present and non-empty.
    """
    schema = get_agent_input_schema(agent_name)
    if not schema:
        return True, None
    for key, spec in schema.items():
        if not isinstance(spec, dict):
            continue
        required = spec.get("required", "default" not in spec)
        if required and key not in configuration:
            return False, f"Missing required parameter: {key}"
        val = configuration.get(key)
        if required and (val is None or (isinstance(val, str) and not val.strip())):
            return False, f"Required parameter '{key}' must be set"
    return True, None
