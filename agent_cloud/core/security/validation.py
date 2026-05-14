"""Cross-field validation helpers (pure)."""

from __future__ import annotations

import re

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)


def is_uuid_string(value: str) -> bool:
    return bool(_UUID_RE.match((value or "").strip()))
