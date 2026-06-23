"""Repair legacy rolled_back promotion rows -> superseded

Revision ID: k2l3m4n5o6
Revises: j0k1l2m3n4
Create Date: 2026-05-21

"""

from typing import Sequence, Union

from alembic import op

revision: str = "k2l3m4n5o6"
down_revision: Union[str, Sequence[str], None] = "j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_REPAIR_SQL = """
UPDATE agent_deployments AS old
SET status = 'superseded', updated_at = NOW()
WHERE old.status = 'rolled_back'
AND NOT EXISTS (
  SELECT 1 FROM deployment_events e
  WHERE e.deployment_id = old.id AND e.event_type = 'rollback'
)
AND NOT EXISTS (
  SELECT 1 FROM agent_deployments p
  WHERE p.id = old.previous_deployment_id AND p.status = 'active'
)
AND (
  EXISTS (
    SELECT 1 FROM agent_deployments n
    WHERE n.project_id = old.project_id
    AND n.agent_name = old.agent_name
    AND n.status = 'active'
    AND n.id <> old.id
    AND n.created_at > old.created_at
  )
  OR EXISTS (
    SELECT 1 FROM agent_deployments child
    WHERE child.project_id = old.project_id
    AND child.previous_deployment_id = old.id
    AND child.id <> old.id
  )
)
"""


def upgrade() -> None:
    from sqlalchemy import text

    conn = op.get_bind()
    result = conn.execute(text(_REPAIR_SQL))
    count = result.rowcount
    if count and count > 0:
        print(f"[k2l3m4n5o6] Repaired {count} deployment row(s): rolled_back -> superseded")


def downgrade() -> None:
    # Data repair is not reversed — status semantics cannot be inferred safely.
    pass
