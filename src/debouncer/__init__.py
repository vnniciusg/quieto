"""Debouncer — High-performance debounce library for Python.

Provides async and sync debouncing with message coalescing,
designed for LLM-powered applications.

Basic usage:

    from debouncer import Debouncer, DebounceConfig

    debouncer = Debouncer(DebounceConfig(delay=2.0, max_wait=10.0))

    await debouncer.push("hello")
    await debouncer.push("world")
    batch = await debouncer.next_batch()  # ["hello", "world"]

Decorator usage:

    from debouncer import debounce

    @debounce(delay=2.0)
    async def handle(messages: list[str]) -> str:
        return await llm.invoke("\\n".join(messages))
"""

from debouncer.config import DebounceConfig, Strategy
from debouncer.core import Debouncer
from debouncer.decorator import debounce
from debouncer.session import SessionManager
from debouncer.strategies.actor import CoalescingActorStrategy
from debouncer.strategies.adaptive import AdaptiveDebouncer
from debouncer.strategies.base import BaseStrategy
from debouncer.strategies.trailing import TrailingDebouncer

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
