from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.orchestrator import execute_task
from app.models.task import TaskStatus
from app.services.task_service import create_task, get_task


def _explorer_url(signature: str | None) -> str | None:
    if not signature:
        return None
    cluster = "devnet" if "devnet" in settings.SOLANA_RPC_URL else "mainnet-beta"
    return f"https://explorer.solana.com/tx/{signature}?cluster={cluster}"

router = APIRouter(prefix="/agents", tags=["agents"])


class RunTaskRequest(BaseModel):
    task: str = Field(..., min_length=1, description="Task instruction for the agent")
    payment_amount: float = Field(..., gt=0, description="SOL amount to pay on success")


class RunTaskResponse(BaseModel):
    task_id: str
    status: TaskStatus


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    result: str | None
    tx_signature: str | None
    explorer_url: str | None
    error: str | None


async def _run_in_background(task_id: str) -> None:
    """Opens its own DB session so the background task outlives the request session."""
    async with AsyncSessionLocal() as db:
        from app.services.task_service import get_task as _get
        task = await _get(db, task_id)
        if task:
            await execute_task(task, db)


@router.post("/run", response_model=RunTaskResponse, status_code=202)
async def run_agent(
    body: RunTaskRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    task = await create_task(db, task_input=body.task, payment_amount=body.payment_amount)
    background_tasks.add_task(_run_in_background, task.id)
    return RunTaskResponse(task_id=task.id, status=task.status)


@router.post("/run/sync", response_model=TaskStatusResponse)
async def run_agent_sync(
    body: RunTaskRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronous variant: waits for agent + payment to finish before returning.
    Returns the full result + tx_signature in one shot.
    Ideal for demos and testing; use /run (async) in production.
    """
    task = await create_task(db, task_input=body.task, payment_amount=body.payment_amount)

    async with AsyncSessionLocal() as bg_db:
        from app.services.task_service import get_task as _get
        fresh = await _get(bg_db, task.id)
        completed = await execute_task(fresh, bg_db)

    return TaskStatusResponse(
        task_id=completed.id,
        status=completed.status,
        result=completed.result,
        tx_signature=completed.tx_signature,
        explorer_url=_explorer_url(completed.tx_signature),
        error=completed.error,
    )


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    task = await get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        result=task.result,
        tx_signature=task.tx_signature,
        explorer_url=_explorer_url(task.tx_signature),
        error=task.error,
    )
