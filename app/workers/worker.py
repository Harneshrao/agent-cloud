"""
Stateless worker entrypoint used by Docker/Kubernetes:

  python -m app.workers.worker

Runs the full orchestration worker (`workers.worker` — DAG, idempotency, DLQ).
"""

from __future__ import annotations


def main() -> None:
    import workers.worker  # noqa: F401  # side effect: starts task loop


if __name__ == "__main__":
    main()
