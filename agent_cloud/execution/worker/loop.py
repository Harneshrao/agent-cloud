"""
Core worker loop entry — delegates to `workers.execution_worker` reference loop.

The full production worker remains `workers/worker.py` (DAG + idempotency); converge here over time.
"""

from __future__ import annotations


def run_forever() -> None:
    from workers.execution_worker import main

    main()
