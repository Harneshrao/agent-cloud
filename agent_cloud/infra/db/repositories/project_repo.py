"""Project persistence."""

from __future__ import annotations

from uuid import UUID


class ProjectRepository:
    """Placeholder for project membership and ownership checks."""

    def user_can_access(self, project_id: UUID, user_id: UUID) -> bool:
        from database.projects import user_can_access_project

        return user_can_access_project(project_id, user_id)
