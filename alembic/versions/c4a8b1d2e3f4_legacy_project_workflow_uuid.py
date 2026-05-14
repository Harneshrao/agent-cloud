"""legacy_project_id, workflow_nodes/checkpoints UUID, usage_records UUID task_id

Revision ID: c4a8b1d2e3f4
Revises: a967d0437c53
Create Date: 2026-03-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision: str = "c4a8b1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "a967d0437c53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("legacy_project_id", sa.Integer(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_projects_legacy_project_id",
        "projects",
        ["legacy_project_id"],
    )

    # Default seeded project: API X-Project-ID 1 → canonical default project UUID
    op.execute(
        text(
            """
            UPDATE projects
            SET legacy_project_id = 1
            WHERE id = '00000000-0000-4000-8000-000000000002'::uuid
            """
        )
    )

    # Replace runtime-created INTEGER workflow tables with UUID FKs to tasks.id
    op.execute(text("DROP TABLE IF EXISTS workflow_checkpoints CASCADE"))
    op.execute(text("DROP TABLE IF EXISTS workflow_nodes CASCADE"))

    op.create_table(
        "workflow_nodes",
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("agent_name", sa.Text(), nullable=False),
        sa.Column("deps", sa.Text(), nullable=False),
        sa.Column("task_text", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.ForeignKeyConstraint(["workflow_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("workflow_id", "node_id"),
    )
    op.create_index(
        "ix_workflow_nodes_workflow_id",
        "workflow_nodes",
        ["workflow_id"],
        unique=False,
    )

    op.create_table(
        "workflow_checkpoints",
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("node_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("workflow_id", "node_id"),
    )
    op.create_index(
        "ix_workflow_checkpoints_workflow_id",
        "workflow_checkpoints",
        ["workflow_id"],
        unique=False,
    )

    # usage_records: drop legacy INTEGER task_id table if present; recreate with UUID
    op.execute(text("DROP TABLE IF EXISTS usage_records CASCADE"))
    op.create_table(
        "usage_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("agent_name", sa.Text(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("agent_cost", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_records_task_id", "usage_records", ["task_id"])

    op.execute(text("DROP TABLE IF EXISTS agent_run_results CASCADE"))
    op.create_table(
        "agent_run_results",
        sa.Column("run_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("installation_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column("execution_time_ms", sa.Integer(), server_default="0", nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(
        "ix_agent_run_results_installation",
        "agent_run_results",
        ["installation_id"],
    )
    op.create_index(
        "ix_agent_run_results_task",
        "agent_run_results",
        ["task_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_agent_run_results_task", table_name="agent_run_results")
    op.drop_index("ix_agent_run_results_installation", table_name="agent_run_results")
    op.drop_table("agent_run_results")

    op.drop_index("ix_usage_records_task_id", table_name="usage_records")
    op.drop_table("usage_records")

    op.drop_index("ix_workflow_checkpoints_workflow_id", table_name="workflow_checkpoints")
    op.drop_table("workflow_checkpoints")
    op.drop_index("ix_workflow_nodes_workflow_id", table_name="workflow_nodes")
    op.drop_table("workflow_nodes")

    op.drop_constraint("uq_projects_legacy_project_id", "projects", type_="unique")
    op.drop_column("projects", "legacy_project_id")
