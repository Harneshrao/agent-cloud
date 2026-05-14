"""
Worker entrypoint — runs the modular execution loop (`agent_cloud.execution.worker.loop`).

For the full DAG + idempotency worker, continue to run `python -m workers.worker`
from the repo root until migrated into `agent_cloud.execution`.
"""

from __future__ import annotations


def main() -> None:
    from agent_cloud.execution.worker.loop import run_forever

    run_forever()


if __name__ == "__main__":
    main()
