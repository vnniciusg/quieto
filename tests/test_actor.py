"""Tests for the coalescing actor strategy."""

import asyncio

from quieto.strategies.actor import _STOP, CoalescingActorStrategy, debounce_actor


class TestActorCoalescing:
    async def test_basic_coalescing(self):
        rx: asyncio.Queue = asyncio.Queue()
        tx: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(debounce_actor(rx, tx, delay=0.1))

        await rx.put("hi")
        await asyncio.sleep(0.05)
        await rx.put("everything ok?")

        batch = await asyncio.wait_for(tx.get(), timeout=2.0)
        assert batch == ["hi", "everything ok?"]

        await rx.put(_STOP)
        await task

    async def test_separate_batches(self):
        rx: asyncio.Queue = asyncio.Queue()
        tx: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(debounce_actor(rx, tx, delay=0.05))

        await rx.put("first")
        batch1 = await asyncio.wait_for(tx.get(), timeout=1.0)
        assert batch1 == ["first"]

        await rx.put("second")
        batch2 = await asyncio.wait_for(tx.get(), timeout=1.0)
        assert batch2 == ["second"]

        await rx.put(_STOP)
        await task


class TestActorMaxWait:
    async def test_max_wait_forces_flush(self):
        rx: asyncio.Queue = asyncio.Queue()
        tx: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(debounce_actor(rx, tx, delay=1.0, max_wait=0.1))

        await rx.put("msg1")
        batch = await asyncio.wait_for(tx.get(), timeout=0.5)
        assert batch == ["msg1"]

        await rx.put(_STOP)
        await task

    async def test_max_wait_none(self):
        rx: asyncio.Queue = asyncio.Queue()
        tx: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(debounce_actor(rx, tx, delay=0.05, max_wait=None))

        await rx.put("hello")
        batch = await asyncio.wait_for(tx.get(), timeout=1.0)
        assert batch == ["hello"]

        await rx.put(_STOP)
        await task


class TestActorStop:
    async def test_stop_flushes_remaining(self):
        rx: asyncio.Queue = asyncio.Queue()
        tx: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(debounce_actor(rx, tx, delay=10.0))

        await rx.put("pending")
        await asyncio.sleep(0.05)
        await rx.put(_STOP)

        batch = await asyncio.wait_for(tx.get(), timeout=1.0)
        assert batch == ["pending"]
        await task

    async def test_stop_with_empty_buffer(self):
        rx: asyncio.Queue = asyncio.Queue()
        tx: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(debounce_actor(rx, tx, delay=1.0))

        await rx.put(_STOP)
        await asyncio.wait_for(task, timeout=1.0)
        assert tx.empty()


class TestActorBackpressure:
    async def test_backpressure_on_full_output(self):
        rx: asyncio.Queue = asyncio.Queue()
        tx: asyncio.Queue = asyncio.Queue(maxsize=1)
        task = asyncio.create_task(debounce_actor(rx, tx, delay=0.05))

        # First batch fills the output queue
        await rx.put("batch1")
        await asyncio.sleep(0.1)

        # Send more while output is full
        await rx.put("batch2-a")
        await asyncio.sleep(0.02)
        await rx.put("batch2-b")

        # Drain first batch
        b1 = await tx.get()
        assert b1 == ["batch1"]

        # Second batch should have coalesced
        b2 = await asyncio.wait_for(tx.get(), timeout=1.0)
        assert b2 == ["batch2-a", "batch2-b"]

        await rx.put(_STOP)
        await task


class TestCoalescingActorStrategy:
    async def test_push_and_next_batch(self):
        s = CoalescingActorStrategy(delay=0.05, max_wait=1.0)
        s.push("hello")
        batch = await s.next_batch()
        assert batch == ["hello"]

    async def test_multiple_messages_coalesced(self):
        s = CoalescingActorStrategy(delay=0.1, max_wait=1.0)
        s.push("a")
        s.push("b")
        s.push("c")
        batch = await s.next_batch()
        assert batch == ["a", "b", "c"]

    async def test_flush_returns_last_batch(self):
        s = CoalescingActorStrategy(delay=0.05)
        s.push("msg")
        await s.next_batch()
        assert s.flush() == ["msg"]

    async def test_flush_empty(self):
        s = CoalescingActorStrategy(delay=1.0)
        assert s.flush() == []

    async def test_shutdown(self):
        s = CoalescingActorStrategy(delay=10.0)
        s.push("pending")
        await asyncio.sleep(0.05)
        s.shutdown()
        batch = await asyncio.wait_for(s.next_batch(), timeout=1.0)
        assert batch == ["pending"]

    async def test_separate_batches(self):
        s = CoalescingActorStrategy(delay=0.05)
        s.push("first")
        b1 = await s.next_batch()
        assert b1 == ["first"]

        s.push("second")
        b2 = await s.next_batch()
        assert b2 == ["second"]

    async def test_repr(self):
        s = CoalescingActorStrategy(delay=1.0, max_wait=5.0)
        assert repr(s) == "CoalescingActorStrategy(delay=1.0, max_wait=5.0)"
