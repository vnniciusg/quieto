"""Tests for DebounceConfig and Strategy."""

import pytest

from debouncer.config import DebounceConfig, Strategy


class TestStrategy:
    def test_trailing_value(self):
        assert Strategy.TRAILING == "trailing"

    def test_adaptive_value(self):
        assert Strategy.ADAPTIVE == "adaptive"

    def test_actor_value(self):
        assert Strategy.ACTOR == "actor"

    def test_all_are_str(self):
        for s in Strategy:
            assert isinstance(s, str)


class TestDebounceConfig:
    def test_defaults(self):
        cfg = DebounceConfig()
        assert cfg.delay == 2.0
        assert cfg.max_wait == 10.0
        assert cfg.strategy is Strategy.TRAILING

    def test_custom_values(self):
        cfg = DebounceConfig(delay=1.0, max_wait=5.0, strategy=Strategy.TRAILING)
        assert cfg.delay == 1.0
        assert cfg.max_wait == 5.0

    def test_max_wait_none(self):
        cfg = DebounceConfig(delay=1.0, max_wait=None)
        assert cfg.max_wait is None

    def test_delay_zero_raises(self):
        with pytest.raises(ValueError, match="delay must be positive"):
            DebounceConfig(delay=0)

    def test_delay_negative_raises(self):
        with pytest.raises(ValueError, match="delay must be positive"):
            DebounceConfig(delay=-1.0)

    def test_max_wait_zero_raises(self):
        with pytest.raises(ValueError, match="max_wait must be positive"):
            DebounceConfig(delay=1.0, max_wait=0)

    def test_max_wait_negative_raises(self):
        with pytest.raises(ValueError, match="max_wait must be positive"):
            DebounceConfig(delay=1.0, max_wait=-1.0)

    def test_max_wait_less_than_delay_raises(self):
        with pytest.raises(ValueError, match="max_wait.*must be >= delay"):
            DebounceConfig(delay=5.0, max_wait=2.0)

    def test_frozen(self):
        cfg = DebounceConfig()
        with pytest.raises(AttributeError):
            cfg.delay = 5.0  # type: ignore[misc]
