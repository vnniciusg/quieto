"""Tests for strategy registry."""

import pytest

from debouncer.config import DebounceConfig, Strategy
from debouncer.strategies.actor import CoalescingActorStrategy
from debouncer.strategies.adaptive import AdaptiveDebouncer
from debouncer.strategies.registry import build_strategy
from debouncer.strategies.trailing import TrailingDebouncer


class TestBuildStrategy:
    def test_trailing_returns_trailing_debouncer(self):
        cfg = DebounceConfig(strategy=Strategy.TRAILING)
        strategy = build_strategy(cfg)
        assert isinstance(strategy, TrailingDebouncer)

    def test_adaptive_returns_adaptive_debouncer(self):
        cfg = DebounceConfig(strategy=Strategy.ADAPTIVE)
        strategy = build_strategy(cfg)
        assert isinstance(strategy, AdaptiveDebouncer)

    def test_actor_returns_coalescing_actor(self):
        cfg = DebounceConfig(strategy=Strategy.ACTOR)
        strategy = build_strategy(cfg)
        assert isinstance(strategy, CoalescingActorStrategy)

    def test_trailing_passes_config_values(self):
        cfg = DebounceConfig(delay=1.5, max_wait=5.0)
        strategy = build_strategy(cfg)
        assert strategy.delay == 1.5
        assert strategy.max_wait == 5.0

    def test_adaptive_passes_config_values(self):
        cfg = DebounceConfig(delay=0.5, max_wait=3.0, strategy=Strategy.ADAPTIVE)
        strategy = build_strategy(cfg)
        assert strategy.delay == 0.5
        assert strategy.max_wait == 3.0

    def test_actor_passes_config_values(self):
        cfg = DebounceConfig(delay=0.8, max_wait=4.0, strategy=Strategy.ACTOR)
        strategy = build_strategy(cfg)
        assert strategy.delay == 0.8
        assert strategy.max_wait == 4.0

    def test_unknown_strategy_raises(self):
        cfg = DebounceConfig()
        # Monkey-patch the strategy to something unknown
        object.__setattr__(cfg, "strategy", "unknown")
        with pytest.raises(ValueError, match="Unknown strategy"):
            build_strategy(cfg)
