"""Correlation IDs for tracing task_id / request_id across API → worker → DB."""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token
from typing import Optional

_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)


def set_trace_id(value: str | None) -> Token[Optional[str]]:
    v = value or str(uuid.uuid4())
    return _trace_id.set(v)


def get_trace_id() -> str | None:
    return _trace_id.get()


def reset_trace_id(token: Token[Optional[str]]) -> None:
    _trace_id.reset(token)
