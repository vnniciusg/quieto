"""Tests for AdaptiveDebouncer strategy."""

import asyncio
import time

from quieto.strategies.adaptive import AdaptiveDebouncer


class TestAdaptiveDebouncerBasic:
    async def test_single_message(self):
        ad = AdaptiveDebouncer(delay=0.05, max_wait=1.0)
        ad.push("hello")
        batch = await ad.next_batch()
        assert batch == ["hello"]

    async def test_multiple_messages(self):
        ad = AdaptiveDebouncer(delay=0.1, max_wait=1.0)
        ad.push("a")
        ad.push("b")
        batch = await ad.next_batch()
        assert batch == ["a", "b"]

    async def test_flush(self):
        ad = AdaptiveDebouncer(delay=10.0, max_wait=None)
        ad.push("msg")
        result = ad.flush()
        assert result == ["msg"]

    async def test_flush_empty(self):
        ad = AdaptiveDebouncer(delay=1.0)
        result = ad.flush()
        assert result == []

    async def test_shutdown(self):
        ad = AdaptiveDebouncer(delay=10.0)
        ad.push("pending")

        async def shutdown_later():
            await asyncio.sleep(0.05)
            ad.shutdown()

        asyncio.create_task(shutdown_later())
        batch = await ad.next_batch()
        assert batch == ["pending"]


class TestAdaptiveDebouncerAdaptation:
    async def test_delay_adapts_to_fast_input(self):
        ad = AdaptiveDebouncer(
            delay=1.0,
            max_wait=None,
            alpha=0.5,
            multiplier=1.5,
            min_delay=0.01,
            max_delay=5.0,
        )
        # Send messages quickly
        for i in range(5):
            ad.push(f"msg-{i}")
            if i < 4:
                time.sleep(0.02)

        # Delay should have decreased from the initial 1.0
        assert ad.effective_delay < 1.0

        ad.flush()

    async def test_delay_clamped_to_min(self):
        ad = AdaptiveDebouncer(
            delay=1.0,
            max_wait=None,
            alpha=1.0,
            multiplier=0.01,
            min_delay=0.5,
            max_delay=5.0,
        )
        ad.push("a")
        time.sleep(0.01)
        ad.push("b")
        # With alpha=1.0 and multiplier=0.01, delay would be tiny
        # but should be clamped to min_delay
        assert ad.effective_delay >= 0.5
        ad.flush()

    async def test_delay_clamped_to_max(self):
        ad = AdaptiveDebouncer(
            delay=1.0,
            max_wait=None,
            alpha=1.0,
            multiplier=100.0,
            min_delay=0.1,
            max_delay=3.0,
        )
        ad.push("a")
        time.sleep(0.1)
        ad.push("b")
        assert ad.effective_delay <= 3.0
        ad.flush()

    async def test_first_push_does_not_adapt(self):
        ad = AdaptiveDebouncer(delay=1.0, max_wait=None)
        ad.push("first")
        # First push has no previous timestamp, delay should stay at initial
        assert ad.effective_delay == 1.0
        ad.flush()

    async def test_effective_delay_property(self):
        ad = AdaptiveDebouncer(delay=2.0, max_wait=None)
        assert ad.effective_delay == 2.0
