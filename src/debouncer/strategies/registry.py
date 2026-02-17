"""Maps each ``Strategy`` enum member to a callable that builds a ``BaseStrategy``.

When you add a new strategy:

1. Add a variant to the ``Strategy`` enum in ``config.py``.
2. Add an entry to ``REGISTRY`` pointing to a factory function or lambda
   that constructs the concrete strategy from a :class:`DebounceConfig`.
"""

from __future__ import annotations

from collections.abc import Callable

from debouncer.config import DebounceConfig, Strategy
from debouncer.strategies.base import BaseStrategy
from debouncer.strategies.trailing import TrailingDebouncer

StrategyFactory = Callable[[DebounceConfig], BaseStrategy]

REGISTRY: dict[Strategy, StrategyFactory] = {
    Strategy.TRAILING: lambda cfg: TrailingDebouncer(
        delay=cfg.delay,
        max_wait=cfg.max_wait,
    ),
}


def build_strategy(config: DebounceConfig) -> BaseStrategy:
    """Resolve *config.strategy* to a concrete ``BaseStrategy`` instance."""
    factory = REGISTRY.get(config.strategy)
    if not factory:
        raise ValueError(
            f"Unknown strategy: {config.strategy!r}. Registered: {', '.join(s.value for s in REGISTRY)}"
        )
    return factory(config)
