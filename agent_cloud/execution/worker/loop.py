"""
Core worker loop entry — delegates to the canonical production worker.
"""

from __future__ import annotations


def run_forever() -> None:
    from workers.canonical_worker import main

    main()
