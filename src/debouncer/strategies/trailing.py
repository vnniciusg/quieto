"""Trailing-edge debounce strategy with optional max_wait."""

from asyncio import Event, TimerHandle, get_running_loop
from typing import Any

from debouncer.strategies.base import BaseStrategy


class TrailingDebouncer(BaseStrategy):
    """Trailing-edge debounce with max_wait.

    How it works:
        - Buffer incoming events. Each new event resets a timer.
        - When the timer expires (quiet period), fire the accumulated batch.
        - ``max_wait`` caps the maximum time any message can be buffered,
          preventing infinite deferral.

    Example::

        delay=3s, max_wait=10s

        t=0.0s "hi"              -> start timer (3s), start max_wait (10s)
        t=2.0s "everything ok?"  -> reset timer (3s), max_wait still running
        t=5.0s timer expires     -> fire with ["hi", "everything ok?"]

    Complexity:
        Time:   O(1) per event
        Memory: O(n) buffered messages
    """

    __slots__ = (
        "_buffer",
        "_closed",
        "_flush_event",
        "_last_batch",
        "_loop",
        "_max_wait_handle",
        "_timer_handle",
    )

    def __init__(self, delay: float, max_wait: float | None = None) -> None:
        super().__init__(delay, max_wait)
        self._buffer: list[Any] = []
        self._timer_handle: TimerHandle | None = None
        self._max_wait_handle: TimerHandle | None = None
        self._flush_event: Event = Event()
        self._last_batch: list[Any] = []
        self._loop = None
        self._closed = False

    def _get_loop(self):
        if self._loop is None:
            self._loop = get_running_loop()
        return self._loop

    def push(self, message: Any) -> None:
        """Add message to the buffer and reset the delay timer."""
        loop = self._get_loop()

        if not self._buffer and self.max_wait is not None:
            self._max_wait_handle = loop.call_later(self.max_wait, self._do_flush)

        self._buffer.append(message)

        if self._timer_handle is not None:
            self._timer_handle.cancel()

        self._timer_handle = loop.call_later(self.delay, self._do_flush)

    async def next_batch(self) -> list[Any]:
        """Await the next flushed batch."""
        await self._flush_event.wait()
        self._flush_event.clear()
        return self._last_batch

    def flush(self) -> list[Any]:
        """Force-flush any buffered messages immediately."""
        if self._buffer:
            self._do_flush()
        return self._last_batch

    def shutdown(self) -> None:
        """Signal that no more messages will arrive, unblocking waiters."""
        self._closed = True
        self.flush()
        self._flush_event.set()

    def _do_flush(self) -> None:
        if not self._buffer:
            return

        if self._timer_handle is not None:
            self._timer_handle.cancel()
            self._timer_handle = None

        if self._max_wait_handle is not None:
            self._max_wait_handle.cancel()
            self._max_wait_handle = None

        self._last_batch, self._buffer = self._buffer, []
        self._flush_event.set()
