"""
Secret handling — redact sensitive keys from API responses and logs.
"""

from __future__ import annotations

import re
from typing import Any, Dict

_SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|credential|private[_-]?key|"
    r"access[_-]?key|auth|bearer|webhook)",
    re.IGNORECASE,
)


def redact_configuration(config: Dict[str, Any] | None) -> Dict[str, Any]:
    """Return a copy of deployment configuration with likely secrets masked."""
    if not config:
        return {}
    out: Dict[str, Any] = {}
    for key, value in config.items():
        if _SECRET_KEY_PATTERN.search(str(key)):
            out[key] = "***"
        elif isinstance(value, dict):
            out[key] = redact_configuration(value)
        else:
            out[key] = value
    return out
