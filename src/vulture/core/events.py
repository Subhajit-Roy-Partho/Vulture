from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[int, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, run_id: int, event: dict[str, Any]) -> None:
        async with self._lock:
            for queue in list(self._queues.get(run_id, [])):
                await queue.put(event)

    async def subscribe(self, run_id: int) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._queues[run_id].append(queue)

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                if queue in self._queues.get(run_id, []):
                    self._queues[run_id].remove(queue)
