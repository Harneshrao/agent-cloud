"""
Repair legacy promotion rows incorrectly stored as rolled_back.

Before the superseded status existed, version promotion marked prior actives as
rolled_back — the same status used for real user rollbacks. This module converts
promotion leftovers to superseded while preserving genuine rollbacks.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, exists, literal, select, update
from sqlalchemy.orm import Session

from database.models import AgentDeployment, DeploymentEvent
from database.session import SessionLocal

logger = logging.getLogger(__name__)

_repair_ran_globally = False


def should_repair_rolled_back_to_superseded(
    *,
    has_rollback_event: bool,
    prior_version_is_active: bool,
    has_newer_active_same_agent: bool,
) -> bool:
    """Pure predicate mirroring SQL repair rules (for tests)."""
    if has_rollback_event:
        return False
    if prior_version_is_active:
        return False
    return has_newer_active_same_agent


def repair_promotion_rolled_back_rows(
    session: Session,
    project_id: Optional[uuid.UUID] = None,
) -> int:
    """
    Idempotent: rolled_back -> superseded for promotion leftovers.

    Preserves rolled_back when:
    - deployment_events has event_type='rollback' for that deployment, or
    - previous_deployment_id points at a deployment that is still active (user restore).
    """
    old = AgentDeployment
    rollback_ev = DeploymentEvent

    has_rollback = exists(
        select(literal(1))
        .select_from(rollback_ev)
        .where(
            rollback_ev.deployment_id == old.id,
            rollback_ev.event_type == "rollback",
        )
    )
    prior_active = exists(
        select(literal(1))
        .select_from(AgentDeployment)
        .where(
            AgentDeployment.id == old.previous_deployment_id,
            AgentDeployment.status == "active",
        )
    )
    newer_active = exists(
        select(literal(1))
        .select_from(AgentDeployment)
        .where(
            AgentDeployment.project_id == old.project_id,
            AgentDeployment.agent_name == old.agent_name,
            AgentDeployment.status == "active",
            AgentDeployment.id != old.id,
            AgentDeployment.created_at > old.created_at,
        )
    )
    # Direct promotion link (covers older generations when only latest points back one hop).
    superseded_by_child = exists(
        select(literal(1))
        .select_from(AgentDeployment)
        .where(
            AgentDeployment.project_id == old.project_id,
            AgentDeployment.previous_deployment_id == old.id,
            AgentDeployment.id != old.id,
        )
    )

    from sqlalchemy import or_

    filters = [
        old.status == "rolled_back",
        ~has_rollback,
        ~prior_active,
        or_(newer_active, superseded_by_child),
    ]
    if project_id is not None:
        filters.append(old.project_id == project_id)

    now = datetime.now(timezone.utc)
    result = session.execute(
        update(old).where(and_(*filters)).values(status="superseded", updated_at=now)
    )
    return int(result.rowcount or 0)


def repair_all_projects_once() -> int:
    """Run global repair once per process (startup)."""
    global _repair_ran_globally
    if _repair_ran_globally:
        return 0
    with SessionLocal() as session:
        count = repair_promotion_rolled_back_rows(session, project_id=None)
        session.commit()
    _repair_ran_globally = True
    if count:
        logger.info(
            "Repaired %s legacy deployment row(s): rolled_back -> superseded", count
        )
    return count
