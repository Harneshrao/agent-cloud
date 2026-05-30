"""Wave 1 infra: regions routing table + api_keys

Revision ID: j0k1l2m3n4
Revises: i9j0k1l2m3
Create Date: 2026-05-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "j0k1l2m3n4"
down_revision: Union[str, Sequence[str], None] = "i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regions",
        sa.Column("region_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.PrimaryKeyConstraint("region_id"),
    )
    op.execute(
        sa.text(
            """
            INSERT INTO regions (region_id, name, status) VALUES
                ('us', 'US', 'active'),
                ('eu', 'EU', 'active'),
                ('asia', 'Asia', 'active')
            ON CONFLICT (region_id) DO NOTHING
            """
        )
    )

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_hash", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash", name="uq_api_keys_key_hash"),
    )
    op.create_index("idx_api_keys_user", "api_keys", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_api_keys_user", table_name="api_keys")
    op.drop_table("api_keys")
    op.drop_table("regions")
