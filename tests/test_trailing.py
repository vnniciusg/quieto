"""Tests for TrailingDebouncer strategy."""

import asyncio

from quieto.strategies.trailing import TrailingDebouncer


class TestTrailingDebouncerPush:
    async def test_single_message_batch(self):
        td = TrailingDebouncer(delay=0.05)
        td.push("hello")
        batch = await td.next_batch()
        assert batch == ["hello"]

    async def test_multiple_messages_coalesced(self):
        td = TrailingDebouncer(delay=0.1)
        td.push("a")
        td.push("b")
        td.push("c")
        batch = await td.next_batch()
        assert batch == ["a", "b", "c"]

    async def test_timer_resets_on_push(self):
        td = TrailingDebouncer(delay=0.1)
        td.push("first")
        await asyncio.sleep(0.06)
        td.push("second")
        batch = await td.next_batch()
        assert batch == ["first", "second"]

    async def test_push_after_flush_starts_new_cycle(self):
        td = TrailingDebouncer(delay=0.05)
        td.push("batch1")
        batch1 = await td.next_batch()
        assert batch1 == ["batch1"]

        td.push("batch2")
        batch2 = await td.next_batch()
        assert batch2 == ["batch2"]


class TestTrailingDebouncerMaxWait:
    async def test_max_wait_forces_flush(self):
        td = TrailingDebouncer(delay=1.0, max_wait=0.1)
        td.push("a")
        # Keep pushing to reset timer, but max_wait should force flush
        await asyncio.sleep(0.05)
        td.push("b")
        batch = await td.next_batch()
        assert "a" in batch

    async def test_max_wait_none(self):
        td = TrailingDebouncer(delay=0.05, max_wait=None)
        td.push("hello")
        batch = await td.next_batch()
        assert batch == ["hello"]


class TestTrailingDebouncerFlush:
    async def test_manual_flush(self):
        td = TrailingDebouncer(delay=10.0)
        td.push("msg")
        result = td.flush()
        assert result == ["msg"]

    async def test_flush_empty_buffer(self):
        td = TrailingDebouncer(delay=1.0)
        result = td.flush()
        assert result == []

    async def test_flush_clears_buffer(self):
        td = TrailingDebouncer(delay=10.0)
        td.push("a")
        td.push("b")
        td.flush()
        # Second flush should return empty (last_batch still set but buffer empty)
        result = td.flush()
        assert result == ["a", "b"]  # _last_batch is still set


class TestTrailingDebouncerNextBatch:
    async def test_next_batch_blocks_until_flush(self):
        td = TrailingDebouncer(delay=10.0)

        async def push_later():
            await asyncio.sleep(0.05)
            td.push("delayed")
            td.flush()

        asyncio.create_task(push_later())
        batch = await td.next_batch()
        assert batch == ["delayed"]


class TestTrailingDebouncerDoFlush:
    async def test_do_flush_empty_buffer_noop(self):
        td = TrailingDebouncer(delay=1.0)
        td._do_flush()
        assert td._last_batch == []

    async def test_do_flush_swaps_buffer(self):
        td = TrailingDebouncer(delay=10.0)
        td.push("x")
        original_buffer = td._buffer
        td._do_flush()
        # After flush, _last_batch should be the old buffer object
        assert td._last_batch is original_buffer
        assert td._buffer == []


class TestTrailingDebouncerShutdown:
    async def test_shutdown_flushes_and_unblocks(self):
        td = TrailingDebouncer(delay=10.0)
        td.push("pending")

        async def shutdown_later():
            await asyncio.sleep(0.05)
            td.shutdown()

        asyncio.create_task(shutdown_later())
        batch = await td.next_batch()
        assert batch == ["pending"]

    async def test_shutdown_empty_buffer_unblocks(self):
        td = TrailingDebouncer(delay=10.0)

        async def shutdown_later():
            await asyncio.sleep(0.05)
            td.shutdown()

        asyncio.create_task(shutdown_later())
        batch = await td.next_batch()
        assert batch == []

    async def test_shutdown_sets_closed(self):
        td = TrailingDebouncer(delay=1.0)
        td.shutdown()
        assert td._closed is True
