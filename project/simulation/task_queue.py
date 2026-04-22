from __future__ import annotations

from collections import deque

from project.core.models import Task


class TaskQueue:
    """FIFO queue for tasks ready to be scheduled."""

    def __init__(self) -> None:
        self._queue: deque[Task] = deque()

    def enqueue(self, task: Task) -> None:
        self._queue.append(task)

    def extend(self, tasks: list[Task]) -> None:
        self._queue.extend(tasks)

    def pop_all(self) -> list[Task]:
        items = list(self._queue)
        self._queue.clear()
        return items

    def __len__(self) -> int:
        return len(self._queue)

