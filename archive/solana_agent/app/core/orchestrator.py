"""
Orchestrator: manages the full lifecycle of a single task.

Flow:
  pending → running → [agent] → verify → [solana payment] → completed / failed
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.task import Task, TaskStatus
from app.services.agent_runner import run_agent
from app.services.solana_client import send_payment
from app.services.task_service import update_task_status
from app.utils.idempotency import payment_already_sent
from app.utils.retry import with_retry
from app.utils.verifier import verify_result

logger = logging.getLogger(__name__)


async def execute_task(task: Task, db: AsyncSession) -> Task:
    """
    Run the full execution pipeline for a task.
    Returns the updated Task regardless of outcome.
    """
    logger.info("Orchestrator starting task %s", task.id)

    # ── 1. Mark running ───────────────────────────────────────────────────────
    task = await update_task_status(db, task, TaskStatus.RUNNING)

    # ── 2. Run agent (with retry) ─────────────────────────────────────────────
    try:
        agent_result = await with_retry(run_agent, task.task_input)
    except Exception as exc:
        logger.exception("Agent failed all retries for task %s", task.id)
        return await update_task_status(
            db, task, TaskStatus.FAILED, error=f"Agent error: {exc}"
        )

    # ── 3. Verify result ──────────────────────────────────────────────────────
    if not verify_result(agent_result):
        logger.warning("Task %s failed verification: %s", task.id, agent_result.output)
        return await update_task_status(
            db, task, TaskStatus.FAILED, error=agent_result.output
        )

    logger.info("Task %s passed verification — triggering payment", task.id)

    # ── 4. Idempotency check ──────────────────────────────────────────────────
    if payment_already_sent(task):
        logger.warning("Task %s already has tx_signature — skipping payment", task.id)
        return await update_task_status(
            db, task, TaskStatus.COMPLETED, result=agent_result.output
        )

    # ── 5. Trigger Solana payment (with retry) ────────────────────────────────
    try:
        payment = await with_retry(
            send_payment,
            recipient_address=settings.SOLANA_RECIPIENT_ADDRESS,
            amount_sol=float(task.payment_amount),
        )
    except Exception as exc:
        logger.exception("Payment failed for task %s", task.id)
        # Agent succeeded but payment failed — store result, mark failed with reason
        return await update_task_status(
            db,
            task,
            TaskStatus.FAILED,
            result=agent_result.output,
            error=f"Payment error: {exc}",
        )

    if not payment.success:
        logger.error("Payment unsuccessful for task %s: %s", task.id, payment.error)
        return await update_task_status(
            db,
            task,
            TaskStatus.FAILED,
            result=agent_result.output,
            error=f"Payment error: {payment.error}",
        )

    # ── 6. All done ───────────────────────────────────────────────────────────
    logger.info("Task %s completed. tx=%s", task.id, payment.signature)
    return await update_task_status(
        db,
        task,
        TaskStatus.COMPLETED,
        result=agent_result.output,
        tx_signature=payment.signature,
    )
