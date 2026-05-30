"""Product analytics events for activation and PMF measurement

Revision ID: i9j0k1l2m3
Revises: h8i9j0k2l3
Create Date: 2026-05-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "i9j0k1l2m3"
down_revision: Union[str, Sequence[str], None] = "h8i9j0k2l3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("event_name", sa.Text(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deployment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.Text(), nullable=True),
        sa.Column("onboarding_step", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), server_default="client", nullable=False),
        sa.Column(
            "properties",
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_product_events_name_created", "product_events", ["event_name", "created_at"])
    op.create_index("idx_product_events_user_created", "product_events", ["user_id", "created_at"])
    op.create_index("idx_product_events_project_created", "product_events", ["project_id", "created_at"])
    op.create_index("idx_product_events_session", "product_events", ["session_id"])


def downgrade() -> None:
    op.drop_index("idx_product_events_session", table_name="product_events")
    op.drop_index("idx_product_events_project_created", table_name="product_events")
    op.drop_index("idx_product_events_user_created", table_name="product_events")
    op.drop_index("idx_product_events_name_created", table_name="product_events")
    op.drop_table("product_events")
