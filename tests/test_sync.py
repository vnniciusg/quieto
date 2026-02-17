"""Tests for sync wrappers."""

import asyncio

from debouncer._sync import _EventLoopThread, get_shared_loop


class TestEventLoopThread:
    def test_start_and_run_coroutine(self):
        elt = _EventLoopThread()
        elt.start()
        try:

            async def coro():
                return 42

            result = elt.run_coroutine(coro())
            assert result == 42
        finally:
            elt.shutdown()

    def test_start_is_idempotent(self):
        elt = _EventLoopThread()
        elt.start()
        elt.start()  # Should not raise
        elt.shutdown()

    def test_run_coroutine_auto_starts(self):
        elt = _EventLoopThread()
        try:

            async def coro():
                return "auto"

            result = elt.run_coroutine(coro())
            assert result == "auto"
        finally:
            elt.shutdown()

    def test_shutdown_without_start(self):
        elt = _EventLoopThread()
        elt.shutdown()  # Should not raise

    def test_async_operations(self):
        elt = _EventLoopThread()
        elt.start()
        try:

            async def async_op():
                await asyncio.sleep(0.01)
                return "done"

            result = elt.run_coroutine(async_op())
            assert result == "done"
        finally:
            elt.shutdown()


class TestGetSharedLoop:
    def test_returns_event_loop_thread(self):
        loop = get_shared_loop()
        assert isinstance(loop, _EventLoopThread)

    def test_runs_coroutine(self):
        loop = get_shared_loop()

        async def coro():
            return "shared"

        result = loop.run_coroutine(coro())
        assert result == "shared"
