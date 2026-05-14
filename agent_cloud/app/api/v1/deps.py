"""Dependency injection — wire `core` services to `infra` implementations."""

from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from agent_cloud.core.tasks.service import TaskApplicationService
from agent_cloud.infra.config.settings import DEFAULT_PROJECT_UUID
from agent_cloud.infra.db.repositories.task_repo import PostgresTaskRepository
from agent_cloud.infra.redis.queues import RedisReadyQueue


@lru_cache(maxsize=1)
def get_task_service() -> TaskApplicationService:
    default_pid = UUID(str(DEFAULT_PROJECT_UUID).strip())
    return TaskApplicationService(
        tasks=PostgresTaskRepository(),
        queue=RedisReadyQueue(),
        default_project_id=default_pid,
    )
