"""
Idempotency guard for Solana payments.

Rule: a payment is fired if and only if the task has no tx_signature yet.
This prevents double-payment if the orchestrator is retried after a crash
that happened after the transaction was confirmed but before the DB write.
"""

from app.models.task import Task


def payment_already_sent(task: Task) -> bool:
    """Return True if a transaction signature is already stored for this task."""
    return bool(task.tx_signature)
