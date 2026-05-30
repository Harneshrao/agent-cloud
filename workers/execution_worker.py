"""
Deprecated reference loop — delegates to the canonical worker.

Prefer: python -m workers.canonical_worker
"""

from __future__ import annotations

import warnings


def main() -> None:
    warnings.warn(
        "workers.execution_worker is deprecated; use workers.canonical_worker",
        DeprecationWarning,
        stacklevel=2,
    )
    from workers.canonical_worker import main as run

    run()


if __name__ == "__main__":
    main()
