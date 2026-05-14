"""task_idempotency: UUID task_id, Alembic-owned DDL

Revision ID: e1f2a3b4c5d6
Revises: c3d4e5f6a7b9
Create Date: 2026-03-21

Replaces any legacy runtime-created table (integer task_id) with UUID FK to tasks.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS task_idempotency CASCADE"))
    op.create_table(
        "task_idempotency",
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("idempotency_key"),
    )
    op.create_index(
        "ix_task_idempotency_task_id",
        "task_idempotency",
        ["task_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_task_idempotency_task_id", table_name="task_idempotency")
    op.drop_table("task_idempotency")
