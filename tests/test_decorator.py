"""Tests for the @debounce decorator."""

import pytest

from debouncer.config import Strategy
from debouncer.core import Debouncer
from debouncer.decorator import ExtractedMessage, _extract_message, debounce


class TestExtractMessage:
    def test_positional_arg(self):
        result = _extract_message(("hello", "extra"), {"key": "val"})
        assert isinstance(result, ExtractedMessage)
        assert result.message == "hello"
        assert result.remaining_args == ("extra",)
        assert result.remaining_kwargs == {"key": "val"}

    def test_keyword_message(self):
        result = _extract_message((), {"message": "hi", "other": 1})
        assert result.message == "hi"
        assert result.remaining_args == ()
        assert result.remaining_kwargs == {"other": 1}

    def test_missing_message_raises(self):
        with pytest.raises(TypeError, match="Missing message argument"):
            _extract_message((), {"other": 1})

    def test_empty_args_and_kwargs(self):
        with pytest.raises(TypeError, match="Missing message argument"):
            _extract_message((), {})

    def test_positional_takes_priority(self):
        result = _extract_message(("pos",), {"message": "kw"})
        assert result.message == "pos"


class TestDebounceDecorator:
    async def test_without_parentheses(self):
        @debounce
        async def handler(messages: list[str]) -> list[str]:
            return messages

        assert hasattr(handler, "debouncer")
        assert hasattr(handler, "flush")
        assert hasattr(handler, "close")

    async def test_with_parentheses(self):
        @debounce(delay=0.5, max_wait=2.0)
        async def handler(messages: list[str]) -> list[str]:
            return messages

        assert isinstance(handler.debouncer, Debouncer)  # type: ignore[attr-defined]

    def test_sync_function_raises(self):
        with pytest.raises(TypeError, match="only supports async function"):

            @debounce
            def handler(messages: list[str]) -> list[str]:  # type: ignore[arg-type]
                return messages

    async def test_decorator_pushes_and_calls(self):
        @debounce(delay=0.05, max_wait=1.0)
        async def handler(messages: list[str]) -> str:
            return ",".join(messages)

        result = await handler("hello")
        assert result == "hello"

    async def test_decorator_with_kwarg_message(self):
        @debounce(delay=0.05, max_wait=1.0)
        async def handler(messages: list[str]) -> str:
            return ",".join(messages)

        result = await handler(message="world")
        assert result == "world"

    async def test_wrapper_attributes(self):
        @debounce(delay=1.0)
        async def handler(messages: list[str]) -> None:
            pass

        assert isinstance(handler.debouncer, Debouncer)  # type: ignore[attr-defined]
        assert callable(handler.flush)  # type: ignore[attr-defined]
        assert callable(handler.close)  # type: ignore[attr-defined]

    async def test_strategy_param(self):
        @debounce(delay=1.0, strategy=Strategy.TRAILING)
        async def handler(messages: list[str]) -> None:
            pass

        assert handler.debouncer.config.strategy is Strategy.TRAILING  # type: ignore[attr-defined]

    async def test_preserves_function_name(self):
        @debounce(delay=1.0)
        async def my_handler(messages: list[str]) -> None:
            pass

        assert my_handler.__name__ == "my_handler"
