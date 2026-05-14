from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class MemoryEntry:
    task: str
    result: str
    timestamp: datetime


class MemoryStore:
    """
    Simple in-memory store for agent task memories.
    """

    def __init__(self) -> None:
        self._memories: List[MemoryEntry] = []

    def store_memory(self, task: str, result: str) -> None:
        """
        Store a new memory entry for a task and its result.
        """
        entry = MemoryEntry(task=task, result=result, timestamp=datetime.utcnow())
        self._memories.append(entry)

    def retrieve_memory(self, task: str) -> List[MemoryEntry]:
        """
        Retrieve previous memories that are related to the given task
        using very simple keyword matching on the task text.
        """
        query = (task or "").lower()
        if not query:
            return []

        keywords = [word for word in query.split() if len(word) > 3]
        if not keywords:
            return []

        related: List[MemoryEntry] = []
        for entry in self._memories:
            task_text = entry.task.lower()
            if any(keyword in task_text for keyword in keywords):
                related.append(entry)

        return related


# Global memory store instance
memory_store = MemoryStore()


if __name__ == "__main__":
    task = "AI startup market"
    result = "AI market is growing rapidly"

    memory_store.store_memory(task, result)

    retrieved = memory_store.retrieve_memory("AI market")
    print("Retrieved memories:", retrieved)


