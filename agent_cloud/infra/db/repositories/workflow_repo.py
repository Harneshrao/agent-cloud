"""Workflow persistence — delegate to legacy `database.workflow_*` during migration."""

from __future__ import annotations

from uuid import UUID


class WorkflowRepository:
    """Placeholder: inject DAG / checkpoint persistence behind this boundary."""

    def get_workflow_root(self, workflow_id: UUID) -> dict | None:
        return None
