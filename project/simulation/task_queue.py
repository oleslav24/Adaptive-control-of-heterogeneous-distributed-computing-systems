"""Task queue primitive used by the simulation runtime."""

from __future__ import annotations

from collections import deque

from project.core.models import Task


class TaskQueue:
    """FIFO queue for tasks ready to be scheduled."""

    def __init__(self) -> None:
        """Initialize empty FIFO queue."""
        self._queue: deque[Task] = deque()

    def enqueue(self, task: Task) -> None:
        """Append one task to queue tail."""
        self._queue.append(task)

    def extend(self, tasks: list[Task]) -> None:
        """Append multiple tasks preserving input order."""
        self._queue.extend(tasks)

    def pop_all(self) -> list[Task]:
        """Pop and return all currently queued tasks."""
        items = list(self._queue)
        self._queue.clear()
        return items

    def peek_all(self) -> list[Task]:
        """Return queued tasks without modifying the queue."""
        return list(self._queue)

    def __len__(self) -> int:
        """Return current queue size."""
        return len(self._queue)
