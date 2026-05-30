"""
Production worker entrypoint used by Docker/Kubernetes:

  python -m app.workers.worker

Canonical loop: guaranteed_loop + agent_executor (DAG, v2, retry, DLQ).
"""

from __future__ import annotations


def main() -> None:
    from workers.canonical_worker import main as run

    run()


if __name__ == "__main__":
    main()
