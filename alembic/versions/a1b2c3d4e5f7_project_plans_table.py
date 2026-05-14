"""project_plans: project → plan history (UUID project_id)

Revision ID: a1b2c3d4e5f7
Revises: f8a9b0c1d2e3
Create Date: 2026-03-21

Replaces runtime INTEGER project_id DDL with UUID FK to projects.id.

- Ensures `plans` exists and seeds the Free plan (same defaults as database.plans.ensure_free_plan)
  so fresh DBs satisfy FKs without running the app first.
- If a legacy `project_plans` table exists with INTEGER `project_id`, rows are copied into a
  temp table by joining `projects.legacy_project_id = project_plans.project_id`. Rows with no
  matching legacy row are dropped (no stable UUID mapping).

If this revision was already applied from an older script without the above logic, run
`alembic upgrade head` — revision `b2c3d4e5f6a8` idempotently ensures `plans` + Free.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_plans_table_and_free(conn) -> None:
    """Runtime historically created `plans`; mirror that DDL and seed Free for FK + quotas."""
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS plans (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                monthly_run_limit INTEGER NOT NULL,
                monthly_execution_time_limit_ms INTEGER NOT NULL,
                price_usd REAL NOT NULL,
                created_at TIMESTAMP
            )
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO plans (id, name, monthly_run_limit, monthly_execution_time_limit_ms, price_usd, created_at)
            SELECT
                (SELECT COALESCE(MAX(id), 0) + 1 FROM plans AS p2),
                'Free',
                1000,
                600000,
                0.0,
                NOW() AT TIME ZONE 'UTC'
            WHERE NOT EXISTS (SELECT 1 FROM plans WHERE name = 'Free')
            """
        )
    )


def upgrade() -> None:
    conn = op.get_bind()
    _ensure_plans_table_and_free(conn)

    has_pp = conn.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'project_plans'
            )
            """
        )
    ).scalar()

    project_id_type = None
    if has_pp:
        project_id_type = conn.execute(
            text(
                """
                SELECT data_type FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'project_plans'
                  AND column_name = 'project_id'
                """
            )
        ).scalar()

    # Already UUID schema (e.g. re-run / repaired DB): do not drop data.
    if project_id_type == "uuid":
        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS idx_project_plans_project_id
                ON project_plans (project_id)
                """
            )
        )
        return

    if has_pp and project_id_type in ("integer", "bigint", "smallint"):
        conn.execute(
            text(
                """
                CREATE TEMP TABLE _project_plans_uuid_mig AS
                SELECT p.id AS project_id, pp.plan_id, pp.started_at
                FROM project_plans AS pp
                INNER JOIN projects AS p ON p.legacy_project_id = pp.project_id
                """
            )
        )

    op.execute(text("DROP TABLE IF EXISTS project_plans CASCADE"))
    op.create_table(
        "project_plans",
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["plans.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("project_id", "started_at"),
    )
    op.create_index(
        "idx_project_plans_project_id",
        "project_plans",
        ["project_id"],
        unique=False,
    )

    if has_pp and project_id_type in ("integer", "bigint", "smallint"):
        conn.execute(
            text(
                """
                INSERT INTO project_plans (project_id, plan_id, started_at)
                SELECT project_id, plan_id, started_at FROM _project_plans_uuid_mig
                """
            )
        )


def downgrade() -> None:
    op.drop_index("idx_project_plans_project_id", table_name="project_plans")
    op.drop_table("project_plans")
