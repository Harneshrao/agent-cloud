from __future__ import annotations

from typing import Any, Dict

from engine.stream_store import append_event


class RunLogger:
    """
    Simple per-run logger that writes structured events into the in-memory
    stream store so the dashboard can surface progress for a task.
    """

    def __init__(self, task_id: int, run_id: int | None, agent_name: str) -> None:
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
            event["run_id"] = self._run_id
        if fields:
            event.update(fields)
        append_event(self._task_id, event)

    def info(self, message: str, **fields: Any) -> None:
        self._emit("info", message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        self._emit("warning", message, **fields)

    def error(self, message: str, **fields: Any) -> None:
        self._emit("error", message, **fields)

