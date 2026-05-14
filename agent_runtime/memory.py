from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


_SHORT_TERM: Dict[Tuple[str, int], Dict[str, Any]] = {}
_LONG_TERM: Dict[Tuple[str, Optional[int]], List[Dict[str, Any]]] = {}


class Memory:
    """
    Minimal memory abstraction for agents.

    This implementation is intentionally simple and in-memory only; it keeps the
    public API stable so it can later be wired to SQLite/Postgres without
    changing agent code.
    """

    def __init__(self, agent_name: str, task_id: int, project_id: Optional[int] = None) -> None:
        self.agent_name = agent_name
        self.task_id = task_id
        self.project_id = project_id

    # Short term memory: scoped to (agent_name, task_id)
    def put_short(self, key: str, value: Any) -> None:
        bucket_key = (self.agent_name, self.task_id)
        bucket = _SHORT_TERM.setdefault(bucket_key, {})
        bucket[key] = value

    def get_short(self, key: str, default: Any = None) -> Any:
        bucket_key = (self.agent_name, self.task_id)
        bucket = _SHORT_TERM.get(bucket_key, {})
        return bucket.get(key, default)

    # Long term memory: scoped to (agent_name, project_id)
    def append_long(self, namespace: str, data: Dict[str, Any]) -> None:
        bucket_key = (self.agent_name, self.project_id)
        bucket = _LONG_TERM.setdefault(bucket_key, [])
        entry = {"namespace": namespace, **data}
        bucket.append(entry)

    def query_long(self, namespace: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        bucket_key = (self.agent_name, self.project_id)
        bucket = list(_LONG_TERM.get(bucket_key, []))
        if namespace is not None:
            bucket = [e for e in bucket if e.get("namespace") == namespace]
        return bucket[-limit:]

