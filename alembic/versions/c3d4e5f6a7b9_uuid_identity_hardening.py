"""Drop legacy_project_id; optional users.name; project_members UUID table

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
Create Date: 2026-03-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "c3d4e5f6a7b9"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    has_legacy = conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'projects'
                  AND column_name = 'legacy_project_id'
            )
            """
        )
    ).scalar()
    if has_legacy:
        op.drop_constraint("uq_projects_legacy_project_id", "projects", type_="unique")
        op.drop_column("projects", "legacy_project_id")

    op.execute(
        text(
            """
            ALTER TABLE users ADD COLUMN IF NOT EXISTS name TEXT
            """
        )
    )

    op.execute(text("DROP TABLE IF EXISTS project_members CASCADE"))
    op.create_table(
        "project_members",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "project_id", "user_id", name="uq_project_members_project_user"
        ),
    )
    op.create_index(
        "ix_project_members_project_id",
        "project_members",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_project_members_project_id", table_name="project_members")
    op.drop_table("project_members")
    op.add_column(
        "projects",
        sa.Column("legacy_project_id", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_projects_legacy_project_id",
        "projects",
        ["legacy_project_id"],
    )
    op.drop_column("users", "name")
