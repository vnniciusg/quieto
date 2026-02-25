"""Adaptive debounce strategy with EMA-based delay adjustment."""

import time
from typing import Any

from quieto.strategies.base import BaseStrategy
from quieto.strategies.trailing import TrailingDebouncer


class AdaptiveDebouncer(BaseStrategy):
    """Adaptive debounce that adjusts delay based on user behavior.

    Uses an exponential moving average (EMA) of inter-message intervals
    to dynamically adjust the debounce delay. Fast typists get shorter
    delays; slow, deliberate users get longer delays.

    Args:
        delay: Initial quiet-period delay in seconds.
        max_wait: Maximum time any message can be buffered.
        alpha: EMA smoothing factor (0.0–1.0). Higher = more reactive.
        multiplier: Delay is set to ``ema * multiplier``.
        min_delay: Minimum allowed delay in seconds.
        max_delay: Maximum allowed delay in seconds.

    Complexity:
        Time:   O(1) per event
        Memory: O(1) EMA state + inner buffer
    """

    __slots__ = (
        "_ema",
        "_inner",
        "_last_time",
        "_max_delay",
        "_min_delay",
        "_multiplier",
        "alpha",
    )

    def __init__(
        self,
        delay: float,
        max_wait: float | None = None,
        *,
        alpha: float = 0.3,
        multiplier: float = 1.5,
        min_delay: float = 0.5,
        max_delay: float = 5.0,
    ) -> None:
        super().__init__(delay, max_wait)
        self._inner = TrailingDebouncer(delay=delay, max_wait=max_wait)
        self.alpha = alpha
        self._multiplier = multiplier
        self._min_delay = min_delay
        self._max_delay = max_delay
        self._ema: float = 0.0
        self._last_time: float | None = None

    @property
    def effective_delay(self) -> float:
        """Current dynamically computed delay."""
        return self._inner.delay

    def push(self, message: Any) -> None:
        """Push a message, adapting delay based on inter-message interval."""
        now = time.monotonic()
        if self._last_time is not None:
            interval = now - self._last_time
            self._ema = self.alpha * interval + (1.0 - self.alpha) * self._ema
            new_delay = max(self._min_delay, min(self._max_delay, self._ema * self._multiplier))
            self._inner.delay = new_delay
            self.delay = new_delay
        self._last_time = now
        self._inner.push(message)

    async def next_batch(self) -> list[Any]:
        """Await the next flushed batch."""
        return await self._inner.next_batch()

    def flush(self) -> list[Any]:
        """Force-flush any buffered messages immediately."""
        return self._inner.flush()

    def shutdown(self) -> None:
        """Signal shutdown."""
        self._inner.shutdown()
