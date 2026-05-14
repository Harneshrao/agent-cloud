"""Execution platform: task statuses queued/retry/dead, task columns, task_events, DLQ, rate_limits

Revision ID: f2e3d4c5b6a7
Revises: e1f2a3b4c5d6
Create Date: 2026-03-21

PostgreSQL 15+ recommended (ALTER TYPE ... ADD VALUE IF NOT EXISTS).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2e3d4c5b6a7"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'queued'"))
    op.execute(sa.text("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'retry'"))
    op.execute(sa.text("ALTER TYPE task_status ADD VALUE IF NOT EXISTS 'dead'"))

    op.add_column(
        "tasks",
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("tasks", sa.Column("worker_id", sa.Text(), nullable=True))
    op.add_column("tasks", sa.Column("idempotency_key", sa.Text(), nullable=True))

    op.create_index("idx_tasks_scheduled", "tasks", ["scheduled_at"])
    op.create_index("idx_tasks_status", "tasks", ["status"])
    op.create_index("idx_tasks_project", "tasks", ["project_id"])
    op.create_index(
        "idx_tasks_idempotency",
        "tasks",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.create_table(
        "task_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column(
            "payload",
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
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_task_events_task", "task_events", ["task_id"])

    op.create_table(
        "dead_letter_queue",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "failed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_dlq_task", "dead_letter_queue", ["task_id"])

    op.create_table(
        "rate_limits",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "last_refill",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("rate_limits")
    op.drop_index("idx_dlq_task", table_name="dead_letter_queue")
    op.drop_table("dead_letter_queue")
    op.drop_index("idx_task_events_task", table_name="task_events")
    op.drop_table("task_events")

    op.drop_index("idx_tasks_idempotency", table_name="tasks")
    op.drop_index("idx_tasks_project", table_name="tasks")
    op.drop_index("idx_tasks_status", table_name="tasks")
    op.drop_index("idx_tasks_scheduled", table_name="tasks")

    op.drop_column("tasks", "idempotency_key")
    op.drop_column("tasks", "worker_id")
    op.drop_column("tasks", "completed_at")
    op.drop_column("tasks", "started_at")
    op.drop_column("tasks", "scheduled_at")
    # Enum values queued/retry/dead remain on task_status until manual cleanup.
