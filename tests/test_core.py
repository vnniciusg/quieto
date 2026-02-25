"""Tests for the Debouncer core class."""

import asyncio

import pytest

from quieto.config import DebounceConfig
from quieto.core import Debouncer


class TestDebouncerCreation:
    def test_default_config(self):
        d = Debouncer()
        assert d.config.delay == 2.0
        assert d.config.max_wait == 10.0
        assert d.closed is False

    def test_custom_config(self):
        cfg = DebounceConfig(delay=0.5, max_wait=2.0)
        d = Debouncer(config=cfg)
        assert d.config.delay == 0.5
        assert d.config.max_wait == 2.0


class TestDebouncerDelay:
    def test_delay_getter(self):
        cfg = DebounceConfig(delay=1.5, max_wait=5.0)
        d = Debouncer(config=cfg)
        assert d.delay == 1.5

    def test_delay_setter(self):
        cfg = DebounceConfig(delay=1.0, max_wait=5.0)
        d = Debouncer(config=cfg)
        d.delay = 2.0
        assert d.delay == 2.0

    def test_delay_setter_zero_raises(self):
        d = Debouncer()
        with pytest.raises(ValueError, match="delay must be positive"):
            d.delay = 0

    def test_delay_setter_negative_raises(self):
        d = Debouncer()
        with pytest.raises(ValueError, match="delay must be positive"):
            d.delay = -1.0

    def test_delay_setter_exceeds_max_wait_raises(self):
        cfg = DebounceConfig(delay=1.0, max_wait=5.0)
        d = Debouncer(config=cfg)
        with pytest.raises(ValueError, match="delay.*must be <= max_wait"):
            d.delay = 10.0

    def test_delay_setter_no_max_wait_allows_any(self):
        cfg = DebounceConfig(delay=1.0, max_wait=None)
        d = Debouncer(config=cfg)
        d.delay = 100.0
        assert d.delay == 100.0


class TestDebouncerPushAndBatch:
    async def test_push_and_next_batch(self):
        cfg = DebounceConfig(delay=0.05, max_wait=1.0)
        async with Debouncer(config=cfg) as d:
            await d.push("hello")
            batch = await d.next_batch()
            assert batch == ["hello"]

    async def test_flush(self):
        cfg = DebounceConfig(delay=10.0, max_wait=None)
        d = Debouncer(config=cfg)
        await d.push("msg")
        result = d.flush()
        assert result == ["msg"]


class TestDebouncerClose:
    async def test_close_prevents_push(self):
        d = Debouncer()
        await d.close()
        with pytest.raises(RuntimeError, match="Debouncer is closed"):
            await d.push("msg")

    async def test_close_prevents_next_batch(self):
        d = Debouncer()
        await d.close()
        with pytest.raises(RuntimeError, match="Debouncer is closed"):
            await d.next_batch()

    async def test_close_is_idempotent(self):
        d = Debouncer()
        await d.close()
        await d.close()  # Should not raise
        assert d.closed is True

    async def test_closed_property(self):
        d = Debouncer()
        assert d.closed is False
        await d.close()
        assert d.closed is True


class TestDebouncerContextManager:
    async def test_async_with(self):
        cfg = DebounceConfig(delay=0.05, max_wait=1.0)
        async with Debouncer(config=cfg) as d:
            assert d.closed is False
            await d.push("test")
        assert d.closed is True


class TestDebouncerBatches:
    async def test_batches_iterator(self):
        cfg = DebounceConfig(delay=0.05, max_wait=1.0)
        d = Debouncer(config=cfg)
        collected = []

        async def produce():
            await d.push("a")
            await asyncio.sleep(0.1)
            await d.push("b")
            await asyncio.sleep(0.1)
            await d.close()

        async def consume():
            async for batch in d.batches():
                collected.extend(batch)
                if d.closed:
                    break

        producer = asyncio.create_task(produce())
        consumer = asyncio.create_task(consume())
        await asyncio.gather(producer, consumer)
        assert "a" in collected
        assert "b" in collected


class TestDebouncerRepr:
    def test_repr(self):
        cfg = DebounceConfig(delay=1.0, max_wait=5.0)
        d = Debouncer(config=cfg)
        r = repr(d)
        assert "delay=1.0" in r
        assert "max_wait=5.0" in r
        assert "trailing" in r
        assert "closed=False" in r
