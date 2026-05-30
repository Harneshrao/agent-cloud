"""
Deployment pipeline — upload, validate, deploy, activate, rollback.
"""

from __future__ import annotations

import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from agent_runtime.deployment_storage import (
    save_artifact_bytes,
    storage_path_relative,
    verify_checksum,
)
from agent_runtime.manifest_validation import validate_manifest_from_zip
from database import deployment_store as store

DEPLOYMENT_STATES = frozenset(
    {
        "uploaded",
        "validating",
        "validated",
        "building",
        "ready",
        "deploying",
        "active",
        "failed",
        "rolled_back",
        "archived",
    }
)


def _transition_deployment(
    deployment_id: uuid.UUID,
    status: str,
    event_type: str,
    payload: Optional[dict] = None,
) -> Dict[str, Any]:
    if status not in DEPLOYMENT_STATES:
        raise ValueError(f"invalid deployment status: {status}")
    dep = store.update_deployment(deployment_id, status=status)
    if dep is None:
        raise ValueError("deployment not found")
    store.append_deployment_event(deployment_id, event_type, payload)
    return dep


def upload_artifact(
    project_id: uuid.UUID,
    zip_bytes: bytes,
    version_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist ZIP, validate manifest, return validated artifact record."""
    artifact_id = uuid.uuid4()

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(zip_bytes)
        tmp.flush()
        tmp_path = Path(tmp.name)

    try:
        ok, manifest, errors = validate_manifest_from_zip(tmp_path)
        if not ok:
            raise ValueError("; ".join(errors))

        agent_name = manifest["name"]
        version = (version_override or manifest.get("version") or "0.0.1").strip()
        if not version:
            version = "0.0.1"

        _, checksum = save_artifact_bytes(project_id, artifact_id, zip_bytes)
        rel_path = storage_path_relative(project_id, artifact_id)

        art = store.create_artifact(
            project_id=project_id,
            agent_name=agent_name,
            version=version,
            storage_path=rel_path,
            checksum_sha256=checksum,
            manifest=manifest,
            status="validated",
            artifact_id=artifact_id,
        )
        try:
            from services.usage_metering import record_artifact_uploaded

            record_artifact_uploaded(
                project_id, artifact_id, bytes_size=len(zip_bytes), agent_name=agent_name
            )
        except Exception:
            pass
        try:
            from database import product_events as pe
            from services.product_analytics import track

            track(
                pe.EVENT_ARTIFACT_UPLOAD_SUCCEEDED,
                project_id=project_id,
                properties={"agent": agent_name, "bytes": len(zip_bytes)},
            )
        except Exception:
            pass
        return art
    except Exception:
        raise
    finally:
        tmp_path.unlink(missing_ok=True)


def create_deployment_from_artifact(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    configuration: Optional[dict] = None,
) -> Dict[str, Any]:
    art = store.get_artifact_for_project(artifact_id, project_id)
    if art is None:
        raise ValueError("artifact not found")
    if art["status"] != "validated":
        raise ValueError(f"artifact not validated (status={art['status']})")

    prev = store.find_active_deployment(project_id, art["agent_name"])
    prev_id = uuid.UUID(prev["deployment_id"]) if prev else None

    dep = store.create_deployment(
        project_id=project_id,
        artifact_id=artifact_id,
        agent_name=art["agent_name"],
        version=art["version"],
        status="uploaded",
        configuration=configuration or {},
        previous_deployment_id=prev_id,
    )
    dep_id = uuid.UUID(dep["deployment_id"])

    try:
        for status in ("validating", "validated", "building", "ready", "deploying"):
            _transition_deployment(dep_id, status, f"state_{status}")

        store.supersede_active_deployments(project_id, art["agent_name"], dep_id)
        store.update_deployment(
            dep_id,
            status="active",
            activated_at=datetime.now(timezone.utc),
        )
        store.append_deployment_event(
            dep_id, "activated", {"artifact_id": str(artifact_id)}
        )
        return store.get_deployment(dep_id) or dep
    except Exception as e:
        _transition_deployment(
            dep_id, "failed", "deploy_failed", {"error": str(e)}
        )
        raise


def rollback_deployment(
    project_id: uuid.UUID, deployment_id: uuid.UUID
) -> Dict[str, Any]:
    dep = store.get_deployment_for_project(deployment_id, project_id)
    if dep is None:
        raise ValueError("deployment not found")
    if dep["status"] != "active":
        raise ValueError("only active deployments can be rolled back")

    dep_uuid = uuid.UUID(dep["deployment_id"])
    _transition_deployment(
        dep_uuid, "rolled_back", "rollback", {"reason": "user_requested"}
    )

    prev_id = dep.get("previous_deployment_id")
    if prev_id:
        prev_uuid = uuid.UUID(prev_id)
        prev = store.get_deployment(prev_uuid)
        if prev:
            store.supersede_active_deployments(project_id, dep["agent_name"], prev_uuid)
            store.update_deployment(
                prev_uuid,
                status="active",
                activated_at=datetime.now(timezone.utc),
            )
            store.append_deployment_event(
                prev_uuid, "reactivated", {"from_rollback": str(dep_uuid)}
            )
            return store.get_deployment(prev_uuid) or prev

    return store.get_deployment(dep_uuid) or dep


def get_deployment_health(deployment_id: uuid.UUID) -> Dict[str, Any]:
    dep = store.get_deployment(deployment_id)
    if dep is None:
        raise ValueError("deployment not found")
    art = store.get_artifact(uuid.UUID(dep["artifact_id"]))
    healthy = dep["status"] == "active" and art is not None and art["status"] == "validated"
    path_ok = False
    if art:
        from agent_runtime.deployment_storage import resolve_artifact_path

        p = resolve_artifact_path(art["storage_path"])
        path_ok = verify_checksum(p, art["checksum_sha256"])
    return {
        "deployment_id": dep["deployment_id"],
        "project_id": dep["project_id"],
        "artifact_version": dep["version"],
        "runtime_version": (art or {}).get("manifest", {}).get("runtime", "python"),
        "status": dep["status"],
        "healthy": healthy and path_ok,
        "checksum_ok": path_ok,
    }
