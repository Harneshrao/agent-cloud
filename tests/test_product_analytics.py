"""Product analytics event storage."""

from __future__ import annotations

import uuid

import pytest

from database import product_events as pe


@pytest.mark.skipif(
    not __import__("os").environ.get("DATABASE_URL"),
    reason="DATABASE_URL required",
)
def test_insert_and_has_project_event():
    project_id = uuid.uuid4()
    pe.insert_product_event(
        pe.EVENT_ONBOARDING_STEP,
        project_id=project_id,
        onboarding_step="deployed",
        source="test",
    )
    assert pe.has_project_event(project_id, pe.EVENT_ONBOARDING_STEP)
    assert not pe.has_project_event(project_id, pe.EVENT_FIRST_TASK_COMPLETED)
