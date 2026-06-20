from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import json

from app.core.config import get_settings


@dataclass(frozen=True)
class QueuedJob:
    job_id: str


class MemoryJobQueue:
    """In-memory queue for local worker tests and demos."""

    def __init__(self) -> None:
        self._items: deque[str] = deque()

    def enqueue(self, job_id: str) -> None:
        if job_id not in self._items:
            self._items.append(job_id)

    def dequeue(self) -> QueuedJob | None:
        if not self._items:
            return None
        return QueuedJob(job_id=self._items.popleft())

    def size(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()


class RedisJobQueue:
    """Redis-backed queue boundary for pilot deployment wiring."""

    key = "therapist-app-v2:jobs"

    def __init__(self, redis_url: str) -> None:
        try:
            import redis
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("Redis job queue mode requires the redis package.") from exc
        self.client = redis.from_url(redis_url)

    def enqueue(self, job_id: str) -> None:
        self.client.rpush(self.key, json.dumps({"job_id": job_id}))

    def dequeue(self) -> QueuedJob | None:
        item = self.client.lpop(self.key)
        if item is None:
            return None
        payload = json.loads(item)
        return QueuedJob(job_id=payload["job_id"])

    def size(self) -> int:
        return int(self.client.llen(self.key))

    def clear(self) -> None:
        self.client.delete(self.key)


_memory_queue = MemoryJobQueue()


def get_job_queue():
    settings = get_settings()
    if settings.job_queue_mode == "memory":
        return _memory_queue
    if settings.job_queue_mode == "redis":
        return RedisJobQueue(settings.redis_url)
    raise RuntimeError(f"Unsupported job queue mode: {settings.job_queue_mode}")
