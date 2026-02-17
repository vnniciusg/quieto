"""Core Debouncer class — main entry point for the library."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from debouncer.strategies.registry import build_strategy

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from debouncer.strategies.base import BaseStrategy

from debouncer.config import DebounceConfig


class Debouncer:
    __slots__ = ("_closed", "_config", "_strategy")

    def __init__(self, *, config: DebounceConfig | None = None) -> None:
        self._config = config or DebounceConfig()
        self._strategy: BaseStrategy = build_strategy(self._config)
        self._closed = False

    @property
    def config(self) -> DebounceConfig:
        return self._config

    @property
    def delay(self) -> float:
        return self._strategy.delay

    @delay.setter
    def delay(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"delay must be positive, got {value}")
        if self._strategy.max_wait is not None and value > self._strategy.max_wait:
            raise ValueError(f"delay ({value}) must be <= max_wait ({self._strategy.max_wait})")
        self._strategy.delay = value

    @property
    def closed(self) -> bool:
        return self._closed

    async def push(self, message: Any) -> None:
        self._ensure_open()
        self._strategy.push(message)

    async def next_batch(self) -> list[Any]:
        self._ensure_open()
        return await self._strategy.next_batch()

    def flush(self) -> list[Any]:
        return self._strategy.flush()

    async def batches(self) -> AsyncIterator[list[Any]]:
        """Iterate over debounced batches until closed."""
        while not self._closed:
            batch = await self._strategy.next_batch()
            if self._closed and not batch:
                break
            yield batch

    async def close(self) -> None:
        """Close debouncer and flush pending messages."""
        if self._closed:
            return
        self._closed = True
        self._strategy.shutdown()

    async def __aenter__(self) -> Debouncer:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Debouncer is closed")

    def __repr__(self) -> str:
        return (
            f"Debouncer(delay={self._config.delay}, "
            f"max_wait={self._config.max_wait}, "
            f"strategy={self._config.strategy.value}, "
            f"closed={self._closed})"
        )
