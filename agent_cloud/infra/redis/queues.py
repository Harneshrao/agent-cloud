"""Ready queue — LIST operations (canonical keys from config.redis_keys)."""

from __future__ import annotations

from uuid import UUID

from agent_cloud.core.tasks.ports import TaskQueuePort
from redis_queue_pkg.redis_queue import get_task_queue


class RedisReadyQueue(TaskQueuePort):
    """Adapter: core `TaskQueuePort` → existing `redis_queue_pkg.TaskQueue`."""

    def enqueue_ready(self, task_id: UUID) -> None:
        get_task_queue().enqueue_ready(str(task_id))
