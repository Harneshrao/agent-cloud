"""
Global task router: assign target_region when tasks are created.

Routing considers user location (user_region), worker availability (active regions),
and fallback to a default region when user_region is not available.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from database.regions import get_region, get_default_region


def route_task(task_payload: Dict[str, Any], user_region: Optional[str] = None) -> Optional[str]:
    """
    Decide target_region for a task.

    Policy:
      - If user_region is available and is an active region, route to that region.
      - Else route to closest/default region (first active region, e.g. us).

    Returns:
      region_id string (e.g. 'us', 'eu', 'asia') or None (no region constraint;
      any worker may take the task).
    """
    if user_region and str(user_region).strip():
        region_id = str(user_region).strip().lower()
        r = get_region(region_id)
        if r is not None and (r.get("status") or "").lower() == "active":
            return region_id
    default = get_default_region()
    return default
