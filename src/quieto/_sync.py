"""Synchronous wrappers for async debouncer operations.

Manages a background event loop thread for sync-to-async bridging.
"""

import asyncio
import threading
from typing import Any


class _EventLoopThread:
    """Manages a background event loop for sync-to-async bridging."""

    __slots__ = ("_loop", "_started", "_thread")

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._started = threading.Event()

    def start(self) -> None:
        """Start the background event loop thread (idempotent)."""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._started.wait()

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._started.set()
        self._loop.run_forever()

    def run_coroutine(self, coro: Any) -> Any:
        """Submit a coroutine to the background loop and block for the result."""
        if self._loop is None:
            self.start()
        assert self._loop is not None
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    def shutdown(self) -> None:
        """Stop the background event loop and join the thread."""
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
            self._loop = None
            self._started.clear()


# Module-level shared event loop thread for sync operations
_shared_loop = _EventLoopThread()


def get_shared_loop() -> _EventLoopThread:
    """Return the shared background event loop thread, starting it if needed."""
    _shared_loop.start()
    return _shared_loop
