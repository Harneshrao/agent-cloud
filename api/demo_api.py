from __future__ import annotations

import json
import uuid
from typing import Dict, Optional

from fastapi import APIRouter, Depends

from api.deps import require_project_can_run
from api.schemas.task_responses import DemoWorkflowStartResponse
from database.db import db
from database.workflow_checkpoints import initialize_workflow
from database.workflow_nodes import insert_nodes, set_node_task_id
from task_queue.task_queue import enqueue_task

router = APIRouter(prefix="/demo", tags=["demo"])


def _create_workflow_root(project_id: uuid.UUID):
    # Root "workflow task" is a placeholder. It should never be fetched by workers,
    # so we set it to a non-pending status.
    task_text = json.dumps({"type": "workflow_root"})
    return db.create_task(task_text=task_text, status="workflow_root", project_id=project_id)


@router.post("/run", response_model=DemoWorkflowStartResponse)
def post_demo_run(context: dict = Depends(require_project_can_run)) -> DemoWorkflowStartResponse:
    """
    Start a minimal 3-node demo workflow (research -> strategy -> content).

    Creates:
    - workflow root task (tasks table)
    - workflow node definitions (workflow_nodes table)
    - workflow checkpoints (workflow_checkpoints table)
    - enqueues only the first node into the existing task queue
    """

    project_id = context["project_id"]

    workflow_id = _create_workflow_root(project_id)

    node1_id = "node1_research"
    node2_id = "node2_strategy"
    node3_id = "node3_content"

    base_task = "Analyze AI startup market"

    nodes = [
        {"id": node1_id, "agent": "research", "deps": [], "task": base_task},
        {"id": node2_id, "agent": "strategy", "deps": [node1_id], "task": base_task},
        {"id": node3_id, "agent": "content", "deps": [node2_id], "task": base_task},
    ]

    # These are the "workflow definitions" + checkpoint rows.
    insert_nodes(workflow_id, nodes)
    initialize_workflow(workflow_id, [node1_id, node2_id, node3_id])

    # Enqueue the first node only.
    node_payload: Dict[str, object] = {
        "task": base_task,
        "agent": "research",
        "runtime": "v2",
        "input": {"task": base_task},
        "workflow_id": workflow_id,
        "node_id": node1_id,
        "deps": [],
    }

    first_task_id = enqueue_task(node_payload, project_id=project_id, user_region=None)
    set_node_task_id(workflow_id, node1_id, first_task_id)

    return DemoWorkflowStartResponse(workflow_id=workflow_id)

