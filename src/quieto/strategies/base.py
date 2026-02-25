"""Abstract base class that all debounce strategies must implement."""

from abc import ABC, abstractmethod
from typing import Any


class BaseStrategy(ABC):
    """Base class for all debounce strategies.

    Every strategy buffers incoming messages and flushes them in batches
    according to its own timing/coalescing rules.

    Subclasses must implement :meth:`push`, :meth:`next_batch`,
    :meth:`flush`, and :meth:`shutdown`.  The constructor handles the
    common ``delay`` and ``max_wait`` parameters.

    Args:
        delay: Quiet-period delay in seconds.  Must be positive.
        max_wait: Maximum time any message can be buffered (seconds).
                  ``None`` disables the cap.  When set, must be >= *delay*.
    """

    __slots__ = ("delay", "max_wait")

    def __init__(self, delay: float, max_wait: float | None = None) -> None:
        if delay <= 0:
            raise ValueError(f"delay must be positive, got {delay}")

        if max_wait is not None and max_wait <= 0:
            raise ValueError(f"max_wait must be positive, got {max_wait}")

        self.delay = delay
        self.max_wait = max_wait

    @abstractmethod
    def push(self, message: Any) -> None:
        """Add a message to the internal buffer."""

    @abstractmethod
    async def next_batch(self) -> list[Any]:
        """Wait for the next flushed batch and return it."""

    @abstractmethod
    def flush(self) -> list[Any]:
        """Force-flush buffered messages and return them immediately."""

    @abstractmethod
    def shutdown(self) -> None:
        """Signal shutdown to unblock any waiters."""

    def __repr__(self) -> str:
        return f"{type(self).__name__}(delay={self.delay}, max_wait={self.max_wait})"
