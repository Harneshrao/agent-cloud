"""HTTP response envelopes."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Ok(BaseModel, Generic[T]):
    data: T


class ErrorBody(BaseModel):
    detail: str
    code: str | None = None
    meta: dict[str, Any] | None = None
