"""dead_letter_tasks / task_retries: INTEGER → UUID (drop legacy, recreate)

Revision ID: f8a9b0c1d2e3
Revises: c4a8b1d2e3f4
Create Date: 2026-03-21

Runtime `database.dead_letter` previously used CREATE TABLE IF NOT EXISTS with
INTEGER task_id/workflow_id. Those tables are incompatible with UUID tasks.id.
This migration drops them if present (data loss for dead-letter / retry rows)
and recreates them with UUID keys aligned with `tasks`.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, Sequence[str], None] = "c4a8b1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Order-independent: no FK between these two.
    op.execute(text("DROP TABLE IF EXISTS dead_letter_tasks CASCADE"))
    op.execute(text("DROP TABLE IF EXISTS task_retries CASCADE"))

    op.create_table(
        "dead_letter_tasks",
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=True),
        sa.Column("node_id", sa.Text(), nullable=True),
        sa.Column("agent_name", sa.Text(), nullable=True),
        sa.Column("task_payload", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("task_id", name="dead_letter_tasks_pkey"),
    )
    op.execute(
        text(
            "CREATE INDEX idx_dead_letter_created_at ON dead_letter_tasks (created_at DESC)"
        )
    )

    op.create_table(
        "task_retries",
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.PrimaryKeyConstraint("task_id", name="task_retries_pkey"),
    )


def downgrade() -> None:
    op.drop_table("task_retries")
    op.drop_table("dead_letter_tasks")

    op.create_table(
        "dead_letter_tasks",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=True),
        sa.Column("node_id", sa.Text(), nullable=True),
        sa.Column("agent_name", sa.Text(), nullable=True),
        sa.Column("task_payload", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("task_id", name="dead_letter_tasks_pkey"),
    )
    op.create_index(
        "idx_dead_letter_created_at",
        "dead_letter_tasks",
        ["created_at"],
        unique=False,
    )
    op.create_table(
        "task_retries",
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column(
            "retry_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.PrimaryKeyConstraint("task_id", name="task_retries_pkey"),
    )
