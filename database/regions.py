"""
Regions for global task routing.

Table: regions (region_id PRIMARY KEY, name, status)
Example regions: us, eu, asia (status 'active').
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from database.db import db

DEFAULT_REGIONS = [
    ("us", "US", "active"),
    ("eu", "EU", "active"),
    ("asia", "Asia", "active"),
]


def _ensure_schema() -> None:
    """Schema from Alembic only; no runtime DDL."""
    return


def get_region(region_id: str) -> Optional[Dict[str, Any]]:
    """Return region by region_id, or None."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        "SELECT region_id, name, status FROM regions WHERE region_id = ?",
        (region_id.strip().lower(),),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {
        "region_id": row["region_id"],
        "name": row["name"],
        "status": row["status"],
    }


def list_active_regions() -> List[Dict[str, Any]]:
    """Return all regions with status = 'active', ordered by region_id."""
    _ensure_schema()
    cur = db.get_connection().cursor()
    cur.execute(
        """
        SELECT region_id, name, status
        FROM regions
        WHERE status = 'active'
        ORDER BY region_id
        """
    )
    return [
        {"region_id": r["region_id"], "name": r["name"], "status": r["status"]}
        for r in cur.fetchall()
    ]


def get_default_region() -> Optional[str]:
    """Return the first active region_id (fallback for routing). Typically 'us'."""
    regions = list_active_regions()
    return regions[0]["region_id"] if regions else None
