"""Deployment application service — wedge control plane."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from agent_cloud.core.deployments import pipeline
from database import deployment_store as store


class DeploymentState(str, Enum):
    uploaded = "uploaded"
    validating = "validating"
    validated = "validated"
    building = "building"
    ready = "ready"
    deploying = "deploying"
    active = "active"
    failed = "failed"
    rolled_back = "rolled_back"
    superseded = "superseded"
    archived = "archived"


class DeploymentApplicationService:
    """Project-scoped deployments backed by agent_deployments + agent_artifacts."""

    def upload_artifact(
        self,
        project_id: uuid.UUID,
        zip_bytes: bytes,
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        return pipeline.upload_artifact(project_id, zip_bytes, version_override=version)

    def list_artifacts(
        self, project_id: uuid.UUID, agent_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return store.list_artifacts(project_id, agent_name=agent_name)

    def get_artifact(
        self, project_id: uuid.UUID, artifact_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        return store.get_artifact_for_project(artifact_id, project_id)

    def deploy(
        self,
        project_id: uuid.UUID,
        artifact_id: uuid.UUID,
        configuration: Optional[dict] = None,
    ) -> Dict[str, Any]:
        return pipeline.create_deployment_from_artifact(
            project_id, artifact_id, configuration=configuration
        )

    def list_for_project(
        self, project_id: uuid.UUID, agent_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return store.list_deployments(project_id, agent_name=agent_name)

    def get(
        self, project_id: uuid.UUID, deployment_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        return store.get_deployment_for_project(deployment_id, project_id)

    def transition(
        self, project_id: uuid.UUID, deployment_id: uuid.UUID, target: DeploymentState
    ) -> bool:
        dep = store.get_deployment_for_project(deployment_id, project_id)
        if dep is None:
            return False
        store.update_deployment(deployment_id, status=target.value)
        store.append_deployment_event(
            deployment_id, "status_change", {"status": target.value}
        )
        return True

    def rollback(self, project_id: uuid.UUID, deployment_id: uuid.UUID) -> Dict[str, Any]:
        return pipeline.rollback_deployment(project_id, deployment_id)

    def health(self, deployment_id: uuid.UUID) -> Dict[str, Any]:
        return pipeline.get_deployment_health(deployment_id)

    def events(self, deployment_id: uuid.UUID) -> List[Dict[str, Any]]:
        return store.list_deployment_events(deployment_id)
