from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskStatus


async def create_task(db: AsyncSession, task_input: str, payment_amount: float) -> Task:
    task = Task(task_input=task_input, payment_amount=payment_amount)
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_task(db: AsyncSession, task_id: str) -> Task | None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def update_task_status(
    db: AsyncSession,
    task: Task,
    status: TaskStatus,
    *,
    result: str | None = None,
    tx_signature: str | None = None,
    error: str | None = None,
) -> Task:
    task.status = status
    if result is not None:
        task.result = result
    if tx_signature is not None:
        task.tx_signature = tx_signature
    if error is not None:
        task.error = error
    await db.commit()
    await db.refresh(task)
    return task
