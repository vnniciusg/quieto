"""Debouncer — High-performance debounce library for Python.

Provides async and sync debouncing with message coalescing,
designed for LLM-powered applications.

Basic usage:

    from debouncer import Debouncer, DebounceConfig

    debouncer = Debouncer(DebounceConfig(delay=2.0, max_wait=10.0))

    await quieto.push("hello")
    await quieto.push("world")
    batch = await quieto.next_batch()  # ["hello", "world"]

Decorator usage:

    from debouncer import debounce

    @debounce(delay=2.0)
    async def handle(messages: list[str]) -> str:
        return await llm.invoke("\\n".join(messages))
"""

from quieto.config import DebounceConfig, Strategy
from quieto.core import Debouncer
from quieto.decorator import debounce
from quieto.session import SessionManager
from quieto.strategies.actor import CoalescingActorStrategy
from quieto.strategies.adaptive import AdaptiveDebouncer
from quieto.strategies.base import BaseStrategy
from quieto.strategies.trailing import TrailingDebouncer

__all__ = [
    "AdaptiveDebouncer",
    "BaseStrategy",
    "CoalescingActorStrategy",
    "Debouncer",
    "DebounceConfig",
    "SessionManager",
    "Strategy",
    "TrailingDebouncer",
    "debounce",
]

__version__ = "0.1.0"
