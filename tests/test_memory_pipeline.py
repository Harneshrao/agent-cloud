from __future__ import annotations

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from memory.memory_store import memory_store
from agents.research_agent import run as research_agent_run


def main() -> None:
    task = "AI startup market"
    state = {"task": task}

    # First run: execute the research agent to store a result in memory.
    research_agent_run(state)
    print("First run completed")

    # Second step: retrieve memory for a related query.
    retrieved_memories = memory_store.retrieve_memory("AI market")
    print("Second run retrieved memory:", retrieved_memories)

    if retrieved_memories:
        print("Memory system working")


if __name__ == "__main__":
    main()

