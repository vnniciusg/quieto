"""Thread-safe multi-session manager with per-session debouncing."""

import asyncio
import contextlib
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from debouncer.strategies.actor import _STOP, debounce_actor


@dataclass
class _SessionHandle:
    input_queue: asyncio.Queue[Any]
    output_queue: asyncio.Queue[list[Any]]
    task: asyncio.Task[None]
    last_activity: float = field(default_factory=time.monotonic)


class SessionManager:
    """Manages independent debounce state per session.

    Each session gets its own :func:`debounce_actor` running as an
    ``asyncio.Task``. Idle sessions are garbage-collected after
    ``session_timeout`` seconds.

    Args:
        delay: Quiet-period delay in seconds.
        max_wait: Maximum time any message can be buffered.
        session_timeout: Seconds of inactivity before a session is reaped.
        max_queue_size: Maximum size of each session's input queue.

    Example::

        manager = SessionManager(delay=2.0, max_wait=10.0)
        await manager.start()

        await manager.push("session-123", "hi")
        await manager.push("session-123", "everything ok?")
        batch = await manager.next_batch("session-123")
        # batch == ["hi", "everything ok?"]

        await manager.close()
    """

    __slots__ = (
        "_gc_task",
        "_lock",
        "_sessions",
        "delay",
        "max_queue_size",
        "max_wait",
        "session_timeout",
    )

    def __init__(
        self,
        delay: float = 2.0,
        max_wait: float | None = 10.0,
        session_timeout: float = 300.0,
        max_queue_size: int = 256,
    ) -> None:
        self.delay = delay
        self.max_wait = max_wait
        self.session_timeout = session_timeout
        self.max_queue_size = max_queue_size
        self._sessions: dict[str, _SessionHandle] = {}
        self._lock = threading.Lock()
        self._gc_task: asyncio.Task[None] | None = None

    @property
    def active_sessions(self) -> int:
        """Number of currently active sessions."""
        with self._lock:
            return len(self._sessions)

    async def push(self, session_id: str, message: Any) -> None:
        """Push a message into the given session's debouncer."""
        handle = self._get_or_create(session_id)
        handle.last_activity = time.monotonic()
        await handle.input_queue.put(message)

    async def next_batch(self, session_id: str) -> list[Any]:
        """Await the next debounced batch from a session."""
        handle = self._get_or_create(session_id)
        return await handle.output_queue.get()

    def _get_or_create(self, session_id: str) -> _SessionHandle:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = self._spawn_actor()
            return self._sessions[session_id]

    def _spawn_actor(self) -> _SessionHandle:
        input_q: asyncio.Queue[Any] = asyncio.Queue(maxsize=self.max_queue_size)
        output_q: asyncio.Queue[list[Any]] = asyncio.Queue(maxsize=64)
        task = asyncio.create_task(
            debounce_actor(input_q, output_q, self.delay, self.max_wait)
        )
        return _SessionHandle(
            input_queue=input_q,
            output_queue=output_q,
            task=task,
        )

    async def start(self) -> None:
        """Start the idle-session garbage collection loop."""
        if self._gc_task is None:
            self._gc_task = asyncio.create_task(self._gc_loop())

    async def close(self) -> None:
        """Shut down all sessions and the GC loop."""
        if self._gc_task is not None:
            self._gc_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._gc_task
            self._gc_task = None

        with self._lock:
            for handle in self._sessions.values():
                await handle.input_queue.put(_STOP)
            self._sessions.clear()

    async def _gc_loop(self) -> None:
        """Periodically remove idle sessions."""
        while True:
            await asyncio.sleep(self.session_timeout / 2)
            now = time.monotonic()
            to_remove: list[str] = []
            with self._lock:
                for sid, handle in self._sessions.items():
                    if now - handle.last_activity > self.session_timeout:
                        to_remove.append(sid)
                for sid in to_remove:
                    handle = self._sessions.pop(sid)
                    await handle.input_queue.put(_STOP)

    async def __aenter__(self) -> "SessionManager":
        await self.start()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()
