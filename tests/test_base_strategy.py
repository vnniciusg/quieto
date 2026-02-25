"""Tests for BaseStrategy ABC."""

import pytest

from quieto.strategies.base import BaseStrategy


class TestBaseStrategy:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            BaseStrategy(delay=1.0)  # type: ignore[abstract]

    def test_delay_validation(self):
        class Dummy(BaseStrategy):
            def push(self, message): ...
            async def next_batch(self):
                return []

            def flush(self):
                return []

            def shutdown(self): ...

        with pytest.raises(ValueError, match="delay must be positive"):
            Dummy(delay=0)

    def test_max_wait_validation(self):
        class Dummy(BaseStrategy):
            def push(self, message): ...
            async def next_batch(self):
                return []

            def flush(self):
                return []

            def shutdown(self): ...

        with pytest.raises(ValueError, match="max_wait must be positive"):
            Dummy(delay=1.0, max_wait=-1.0)

    def test_repr(self):
        class Dummy(BaseStrategy):
            def push(self, message): ...
            async def next_batch(self):
                return []

            def flush(self):
                return []

            def shutdown(self): ...

        d = Dummy(delay=1.0, max_wait=5.0)
        assert repr(d) == "Dummy(delay=1.0, max_wait=5.0)"

    def test_repr_no_max_wait(self):
        class Dummy(BaseStrategy):
            def push(self, message): ...
            async def next_batch(self):
                return []

            def flush(self):
                return []

            def shutdown(self): ...

        d = Dummy(delay=1.0)
        assert repr(d) == "Dummy(delay=1.0, max_wait=None)"
