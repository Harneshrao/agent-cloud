from __future__ import annotations

import uuid
from typing import Any, Dict, Union

from engine.stream_store import append_event


class RunLogger:
    """
    Per-run logger: in-memory stream for live UI + durable task_logs via operational_log.
    """

    def __init__(
        self,
        task_id: Union[int, str, uuid.UUID],
        run_id: int | uuid.UUID | None,
        agent_name: str,
    ) -> None:
        self._task_id = task_id
        self._run_id = run_id
        self._agent_name = agent_name

    def _emit(self, level: str, message: str, **fields: Any) -> None:
        event: Dict[str, Any] = {
            "level": level,
            "message": message,
            "agent_name": self._agent_name,
        }
        if self._run_id is not None:
            event["run_id"] = str(self._run_id)
        if fields:
            event.update(fields)
        append_event(self._task_id, event)
        try:
            from agent_cloud.infra.observability.operational_log import log_event

            tid = uuid.UUID(str(self._task_id))
            log_event(
                f"agent_run_{level}",
                message,
                severity=level.upper(),
                task_id=tid,
                persist=True,
                **event,
            )
        except (ValueError, TypeError):
            pass

    def info(self, message: str, **fields: Any) -> None:
        self._emit("info", message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self._emit("warning", message, **fields)

    def error(self, message: str, **fields: Any) -> None:
        self._emit("error", message, **fields)
