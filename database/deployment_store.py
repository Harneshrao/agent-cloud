"""
Persistence for agent artifacts, deployments, and deployment events (SQLAlchemy).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select, update

from database.models import AgentArtifact, AgentDeployment, DeploymentEvent
from database.session import SessionLocal
from security.secrets import redact_configuration


def _iso(dt: Any) -> Any:
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return dt


def _artifact_dict(a: AgentArtifact) -> Dict[str, Any]:
    return {
        "artifact_id": str(a.id),
        "project_id": str(a.project_id),
        "agent_name": a.agent_name,
        "version": a.version,
        "storage_path": a.storage_path,
        "checksum_sha256": a.checksum_sha256,
        "manifest": a.manifest or {},
        "status": a.status,
        "validation_errors": a.validation_errors,
        "created_at": _iso(a.created_at),
    }


def _deployment_dict(d: AgentDeployment, *, redact_secrets: bool = True) -> Dict[str, Any]:
    raw_config = d.configuration or {}
    config = redact_configuration(raw_config) if redact_secrets else dict(raw_config)
    return {
        "deployment_id": str(d.id),
        "project_id": str(d.project_id),
        "artifact_id": str(d.artifact_id),
        "agent_name": d.agent_name,
        "version": d.version,
        "status": d.status,
        "configuration": config,
        "previous_deployment_id": (
            str(d.previous_deployment_id) if d.previous_deployment_id else None
        ),
        "validation_errors": d.validation_errors,
        "created_at": _iso(d.created_at),
        "updated_at": _iso(d.updated_at),
        "activated_at": _iso(d.activated_at) if d.activated_at else None,
    }


def create_artifact(
    project_id: uuid.UUID,
    agent_name: str,
    version: str,
    storage_path: str,
    checksum_sha256: str,
    manifest: dict[str, Any],
    status: str = "uploaded",
    artifact_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    with SessionLocal() as session:
        row = AgentArtifact(
            id=artifact_id or uuid.uuid4(),
            project_id=project_id,
            agent_name=agent_name,
            version=version,
            storage_path=storage_path,
            checksum_sha256=checksum_sha256,
            manifest=manifest,
            status=status,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _artifact_dict(row)


def update_artifact(
    artifact_id: uuid.UUID,
    *,
    status: Optional[str] = None,
    validation_errors: Optional[list] = None,
    manifest: Optional[dict] = None,
) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        row = session.get(AgentArtifact, artifact_id)
        if row is None:
            return None
        if status is not None:
            row.status = status
        if validation_errors is not None:
            row.validation_errors = validation_errors
        if manifest is not None:
            row.manifest = manifest
        session.commit()
        session.refresh(row)
        return _artifact_dict(row)


def get_artifact(artifact_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        row = session.get(AgentArtifact, artifact_id)
        return _artifact_dict(row) if row else None


def list_artifacts(
    project_id: uuid.UUID, agent_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        q = select(AgentArtifact).where(AgentArtifact.project_id == project_id)
        if agent_name:
            q = q.where(AgentArtifact.agent_name == agent_name)
        q = q.order_by(desc(AgentArtifact.created_at))
        return [_artifact_dict(r) for r in session.scalars(q).all()]


def get_artifact_for_project(
    artifact_id: uuid.UUID, project_id: uuid.UUID
) -> Optional[Dict[str, Any]]:
    art = get_artifact(artifact_id)
    if art is None or art["project_id"] != str(project_id):
        return None
    return art


def create_deployment(
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    agent_name: str,
    version: str,
    status: str = "uploaded",
    configuration: Optional[dict] = None,
    previous_deployment_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    with SessionLocal() as session:
        row = AgentDeployment(
            project_id=project_id,
            artifact_id=artifact_id,
            agent_name=agent_name,
            version=version,
            status=status,
            configuration=configuration or {},
            previous_deployment_id=previous_deployment_id,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _deployment_dict(row)


def update_deployment(
    deployment_id: uuid.UUID,
    *,
    status: Optional[str] = None,
    validation_errors: Optional[list] = None,
    configuration: Optional[dict] = None,
    activated_at: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = session.get(AgentDeployment, deployment_id)
        if row is None:
            return None
        if status is not None:
            row.status = status
        if validation_errors is not None:
            row.validation_errors = validation_errors
        if configuration is not None:
            row.configuration = configuration
        if activated_at is not None:
            row.activated_at = activated_at
        row.updated_at = now
        session.commit()
        session.refresh(row)
        return _deployment_dict(row)


def get_deployment(
    deployment_id: uuid.UUID, *, redact_secrets: bool = False
) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        row = session.get(AgentDeployment, deployment_id)
        return _deployment_dict(row, redact_secrets=redact_secrets) if row else None


def get_deployment_for_project(
    deployment_id: uuid.UUID, project_id: uuid.UUID, *, redact_secrets: bool = True
) -> Optional[Dict[str, Any]]:
    dep = get_deployment(deployment_id, redact_secrets=redact_secrets)
    if dep is None or dep["project_id"] != str(project_id):
        return None
    return dep


def list_deployments(
    project_id: uuid.UUID, agent_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        q = select(AgentDeployment).where(AgentDeployment.project_id == project_id)
        if agent_name:
            q = q.where(AgentDeployment.agent_name == agent_name)
        q = q.order_by(desc(AgentDeployment.updated_at))
        return [_deployment_dict(r) for r in session.scalars(q).all()]


def find_active_deployment(
    project_id: uuid.UUID, agent_name: str
) -> Optional[Dict[str, Any]]:
    with SessionLocal() as session:
        row = session.execute(
            select(AgentDeployment)
            .where(
                AgentDeployment.project_id == project_id,
                AgentDeployment.agent_name == agent_name,
                AgentDeployment.status == "active",
            )
            .order_by(desc(AgentDeployment.activated_at))
            .limit(1)
        ).scalar_one_or_none()
        return _deployment_dict(row) if row else None


def supersede_active_deployments(
    project_id: uuid.UUID, agent_name: str, exclude_id: uuid.UUID
) -> int:
    """Mark other active deployments for this agent as rolled_back."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        result = session.execute(
            update(AgentDeployment)
            .where(
                AgentDeployment.project_id == project_id,
                AgentDeployment.agent_name == agent_name,
                AgentDeployment.status == "active",
                AgentDeployment.id != exclude_id,
            )
            .values(status="rolled_back", updated_at=now)
        )
        session.commit()
        return int(result.rowcount or 0)


def append_deployment_event(
    deployment_id: uuid.UUID, event_type: str, payload: Optional[dict] = None
) -> None:
    with SessionLocal() as session:
        session.add(
            DeploymentEvent(
                deployment_id=deployment_id,
                event_type=event_type,
                payload=payload or {},
            )
        )
        session.commit()


def list_deployment_events(
    deployment_id: uuid.UUID, limit: int = 100
) -> List[Dict[str, Any]]:
    with SessionLocal() as session:
        rows = session.scalars(
            select(DeploymentEvent)
            .where(DeploymentEvent.deployment_id == deployment_id)
            .order_by(desc(DeploymentEvent.created_at))
            .limit(limit)
        ).all()
        return [
            {
                "event_id": str(e.id),
                "deployment_id": str(e.deployment_id),
                "event_type": e.event_type,
                "payload": e.payload or {},
                "created_at": _iso(e.created_at),
            }
            for e in rows
        ]
