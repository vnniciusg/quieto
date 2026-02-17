"""Tests for SessionManager."""

import asyncio

from debouncer.session import SessionManager


class TestSessionManagerBasic:
    async def test_push_and_next_batch(self):
        async with SessionManager(delay=0.05, max_wait=1.0) as mgr:
            await mgr.push("s1", "hello")
            batch = await asyncio.wait_for(mgr.next_batch("s1"), timeout=1.0)
            assert batch == ["hello"]

    async def test_multiple_messages_coalesced(self):
        async with SessionManager(delay=0.1, max_wait=1.0) as mgr:
            await mgr.push("s1", "a")
            await mgr.push("s1", "b")
            batch = await asyncio.wait_for(mgr.next_batch("s1"), timeout=1.0)
            assert batch == ["a", "b"]

    async def test_independent_sessions(self):
        async with SessionManager(delay=0.05, max_wait=1.0) as mgr:
            await mgr.push("s1", "session1")
            await mgr.push("s2", "session2")

            b1 = await asyncio.wait_for(mgr.next_batch("s1"), timeout=1.0)
            b2 = await asyncio.wait_for(mgr.next_batch("s2"), timeout=1.0)

            assert b1 == ["session1"]
            assert b2 == ["session2"]

    async def test_active_sessions_count(self):
        async with SessionManager(delay=0.05) as mgr:
            assert mgr.active_sessions == 0
            await mgr.push("s1", "msg")
            assert mgr.active_sessions == 1
            await mgr.push("s2", "msg")
            assert mgr.active_sessions == 2


class TestSessionManagerContextManager:
    async def test_context_manager(self):
        async with SessionManager(delay=0.05) as mgr:
            await mgr.push("s1", "test")
            batch = await asyncio.wait_for(mgr.next_batch("s1"), timeout=1.0)
            assert batch == ["test"]


class TestSessionManagerClose:
    async def test_close_clears_sessions(self):
        mgr = SessionManager(delay=0.05)
        await mgr.start()
        await mgr.push("s1", "msg")
        assert mgr.active_sessions == 1
        await mgr.close()
        assert mgr.active_sessions == 0

    async def test_close_without_start(self):
        mgr = SessionManager(delay=0.05)
        await mgr.close()  # Should not raise
