"""Unified usage_events for metering and quotas

Revision ID: h8i9j0k2l3
Revises: g7h8i9j0k1l2
Create Date: 2026-05-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "h8i9j0k2l3"
down_revision: Union[str, Sequence[str], None] = "g7h8i9j0k1l2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("quantity", sa.Float(), server_default="1", nullable=False),
        sa.Column("unit", sa.Text(), server_default="count", nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deployment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("api_key_id", sa.Integer(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_usage_events_project", "usage_events", ["project_id"])
    op.create_index(
        "idx_usage_events_project_type_created",
        "usage_events",
        ["project_id", "event_type", "created_at"],
    )

    # Optional tier plans (idempotent names; advance serial after explicit Free id=1 seed)
    op.execute(
        sa.text(
            """
            SELECT setval(
                pg_get_serial_sequence('plans', 'id'),
                COALESCE((SELECT MAX(id) FROM plans), 1)
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO plans (name, monthly_run_limit, monthly_execution_time_limit_ms, price_usd, created_at)
            SELECT 'Starter', 10000, 3600000, 29.0, NOW()
            WHERE NOT EXISTS (SELECT 1 FROM plans WHERE name = 'Starter')
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO plans (name, monthly_run_limit, monthly_execution_time_limit_ms, price_usd, created_at)
            SELECT 'Growth', 100000, 36000000, 199.0, NOW()
            WHERE NOT EXISTS (SELECT 1 FROM plans WHERE name = 'Growth')
            """
        )
    )


def downgrade() -> None:
    op.drop_index("idx_usage_events_project_type_created", table_name="usage_events")
    op.drop_index("idx_usage_events_project", table_name="usage_events")
    op.drop_table("usage_events")
