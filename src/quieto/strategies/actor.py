"""Coalescing actor strategy with backpressure via asyncio queues."""

import asyncio
from typing import Any

from quieto.strategies.base import BaseStrategy

_STOP = object()


async def debounce_actor(
    rx: asyncio.Queue[Any],
    tx: asyncio.Queue[list[Any]],
    delay: float,
    max_wait: float | None = None,
) -> None:
    """Run a debounce actor that reads from *rx* and writes batches to *tx*.

    The actor uses ``asyncio.wait_for`` to race between receiving a new
    message and the debounce timer expiring. Backpressure is naturally
    applied when the output queue (*tx*) is full.

    Send the :data:`_STOP` sentinel to *rx* to shut down the actor
    gracefully (any buffered messages are flushed first).

    Args:
        rx: Input queue for incoming messages.
        tx: Output queue for flushed batches.
        delay: Quiet-period delay in seconds.
        max_wait: Maximum time any message can be buffered.
    """
    buffer: list[Any] = []
    deadline: float | None = None
    max_deadline: float | None = None

    loop = asyncio.get_running_loop()

    while True:
        timeout: float | None = None
        if deadline is not None:
            now = loop.time()
            effective_deadline = deadline
            if max_deadline is not None:
                effective_deadline = min(deadline, max_deadline)
            timeout = max(0, effective_deadline - now)

        try:
            if timeout is not None:
                msg = await asyncio.wait_for(rx.get(), timeout=timeout)
            else:
                msg = await rx.get()

            if msg is _STOP:
                if buffer:
                    await tx.put(list(buffer))
                break

            if not buffer and max_wait is not None:
                max_deadline = loop.time() + max_wait

            buffer.append(msg)
            deadline = loop.time() + delay

            if max_deadline is not None:
                deadline = min(deadline, max_deadline)

        except TimeoutError:
            if buffer:
                await tx.put(list(buffer))
                buffer.clear()
                deadline = None
                max_deadline = None


class CoalescingActorStrategy(BaseStrategy):
    """BaseStrategy wrapper around :func:`debounce_actor`.

    Spawns an asyncio task running the actor coroutine. Messages are
    pushed via an input queue and batches are read from an output queue.
    Backpressure is naturally applied when the output queue is full.

    Args:
        delay: Quiet-period delay in seconds.
        max_wait: Maximum time any message can be buffered.
        max_input_queue: Maximum size of the input queue.
        max_output_queue: Maximum size of the output queue.

    Complexity:
        Time:   O(1) per message
        Memory: O(n) buffer + queue overhead
    """

    __slots__ = ("_last_batch", "_rx", "_task", "_tx")

    def __init__(
        self,
        delay: float,
        max_wait: float | None = None,
        *,
        max_input_queue: int = 256,
        max_output_queue: int = 64,
    ) -> None:
        super().__init__(delay, max_wait)
        self._rx: asyncio.Queue[Any] = asyncio.Queue(maxsize=max_input_queue)
        self._tx: asyncio.Queue[list[Any]] = asyncio.Queue(maxsize=max_output_queue)
        self._task: asyncio.Task[None] | None = None
        self._last_batch: list[Any] = []

    def _ensure_task(self) -> None:
        """Start the actor task if not already running."""
        if self._task is None or self._task.done():
            self._task = asyncio.get_running_loop().create_task(
                debounce_actor(self._rx, self._tx, self.delay, self.max_wait)
            )

    def push(self, message: Any) -> None:
        """Push a message into the actor's input queue."""
        self._ensure_task()
        self._rx.put_nowait(message)

    async def next_batch(self) -> list[Any]:
        """Await the next flushed batch from the actor."""
        self._ensure_task()
        self._last_batch = await self._tx.get()
        return self._last_batch

    def flush(self) -> list[Any]:
        """Return the last batch (actor flushes on its own timer)."""
        return self._last_batch

    def shutdown(self) -> None:
        """Send stop sentinel to the actor."""
        self._rx.put_nowait(_STOP)
