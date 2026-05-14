"""Idempotent plans + Free seed for DBs that applied an older a1b2 script

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-03-21

Early deployments may have stamped `a1b2c3d4e5f7` from a minimal migration that only
`DROP`/`CREATE`d `project_plans` without creating `plans` or inserting Free. This revision
only runs the same ensure logic (safe to repeat) so `alembic upgrade head` fixes those DBs
without downgrading.

Does **not** restore `project_plans` rows removed by an earlier blind `DROP` — that history
is unrecoverable without a backup. Only `plans` / Free are ensured here.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "b2c3d4e5f6a8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_plans_table_and_free(conn) -> None:
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


def downgrade() -> None:
    """Do not remove Free or plans — would break FKs and quotas."""
    pass
