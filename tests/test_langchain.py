"""Tests for LangChain middleware integration.

These tests mock LangChain types to avoid requiring langchain as
a test dependency.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import MagicMock  # noqa: I001

import pytest


class _FakeHumanMessage:
    """Minimal stand-in for langchain.messages.HumanMessage."""

    def __init__(self, content: str) -> None:
        self.content = content

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _FakeHumanMessage) and self.content == other.content

    def __repr__(self) -> str:
        return f"HumanMessage({self.content!r})"


class _FakeAIMessage:
    """Minimal stand-in for langchain.messages.AIMessage."""

    def __init__(self, content: str) -> None:
        self.content = content

    def __repr__(self) -> str:
        return f"AIMessage({self.content!r})"


@dataclass
class _FakeModelRequest:
    """Minimal stand-in for ModelRequest."""

    messages: list[Any] = field(default_factory=list)

    def override(self, **kwargs: Any) -> _FakeModelRequest:
        new_msgs = kwargs.get("messages", self.messages)
        return _FakeModelRequest(messages=new_msgs)


@dataclass
class _FakeModelResponse:
    """Minimal stand-in for ModelResponse."""

    content: str = ""


@pytest.fixture(autouse=True)
def _patch_langchain_modules(monkeypatch: pytest.MonkeyPatch):
    """Inject fake langchain modules so the integration can import them."""
    messages_mod = types.ModuleType("langchain.messages")
    messages_mod.HumanMessage = _FakeHumanMessage  # type: ignore[attr-defined]
    messages_mod.AIMessage = _FakeAIMessage  # type: ignore[attr-defined]

    langchain_mod = types.ModuleType("langchain")
    langchain_mod.messages = messages_mod  # type: ignore[attr-defined]

    agents_mod = types.ModuleType("langchain.agents")
    middleware_mod = types.ModuleType("langchain.agents.middleware")
    middleware_mod.AgentMiddleware = object  # type: ignore[attr-defined]
    middleware_mod.ModelRequest = _FakeModelRequest  # type: ignore[attr-defined]
    middleware_mod.ModelResponse = _FakeModelResponse  # type: ignore[attr-defined]
    agents_mod.middleware = middleware_mod  # type: ignore[attr-defined]
    langchain_mod.agents = agents_mod  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "langchain", langchain_mod)
    monkeypatch.setitem(sys.modules, "langchain.messages", messages_mod)
    monkeypatch.setitem(sys.modules, "langchain.agents", agents_mod)
    monkeypatch.setitem(sys.modules, "langchain.agents.middleware", middleware_mod)

    # Force reimport of the integration module so it picks up the fakes
    monkeypatch.delitem(sys.modules, "debouncer.integrations.langchain", raising=False)


def _import_middleware():
    """Import after fakes are patched."""
    from debouncer.integrations.langchain import DebounceMiddleware, _coalesce_human_messages

    return DebounceMiddleware, _coalesce_human_messages


class TestCoalesceHumanMessages:
    def test_empty_list(self):
        _, coalesce = _import_middleware()
        assert coalesce([]) == []

    def test_single_human(self):
        _, coalesce = _import_middleware()
        msgs = [_FakeHumanMessage("hello")]
        result = coalesce(msgs)
        assert len(result) == 1
        assert result[0].content == "hello"

    def test_consecutive_humans_merged(self):
        _, coalesce = _import_middleware()
        msgs = [
            _FakeHumanMessage("hi"),
            _FakeHumanMessage("everything ok?"),
        ]
        result = coalesce(msgs)
        assert len(result) == 1
        assert result[0].content == "hi\neverything ok?"

    def test_non_human_passthrough(self):
        _, coalesce = _import_middleware()
        ai = _FakeAIMessage("I'm fine")
        msgs = [
            _FakeHumanMessage("hello"),
            ai,
            _FakeHumanMessage("bye"),
        ]
        result = coalesce(msgs)
        assert len(result) == 3
        assert result[0].content == "hello"
        assert result[1] is ai
        assert result[2].content == "bye"

    def test_multiple_consecutive_groups(self):
        _, coalesce = _import_middleware()
        msgs = [
            _FakeHumanMessage("a"),
            _FakeHumanMessage("b"),
            _FakeAIMessage("response"),
            _FakeHumanMessage("c"),
            _FakeHumanMessage("d"),
        ]
        result = coalesce(msgs)
        assert len(result) == 3
        assert result[0].content == "a\nb"
        assert result[2].content == "c\nd"


class TestDebounceMiddleware:
    def test_creation(self):
        cls, _ = _import_middleware()
        mw = cls(delay=1.0, max_wait=5.0)
        assert mw.debouncer is not None
        assert mw.debouncer.config.delay == 1.0
        assert mw.debouncer.config.max_wait == 5.0

    def test_wrap_model_call_coalesces(self):
        cls, _ = _import_middleware()
        mw = cls(delay=1.0, coalesce=True)

        request = _FakeModelRequest(
            messages=[
                _FakeHumanMessage("hi"),
                _FakeHumanMessage("how are you?"),
            ]
        )

        handler = MagicMock(return_value=_FakeModelResponse(content="ok"))
        result = mw.wrap_model_call(request, handler)

        handler.assert_called_once()
        passed_request = handler.call_args[0][0]
        assert len(passed_request.messages) == 1
        assert passed_request.messages[0].content == "hi\nhow are you?"
        assert result.content == "ok"

    def test_wrap_model_call_no_coalesce(self):
        cls, _ = _import_middleware()
        mw = cls(delay=1.0, coalesce=False)

        request = _FakeModelRequest(
            messages=[
                _FakeHumanMessage("hi"),
                _FakeHumanMessage("how are you?"),
            ]
        )

        handler = MagicMock(return_value=_FakeModelResponse(content="ok"))
        result = mw.wrap_model_call(request, handler)

        handler.assert_called_once_with(request)
        assert result.content == "ok"

    def test_wrap_model_call_mixed_messages(self):
        cls, _ = _import_middleware()
        mw = cls(delay=1.0)

        request = _FakeModelRequest(
            messages=[
                _FakeHumanMessage("hello"),
                _FakeAIMessage("hi there"),
                _FakeHumanMessage("follow up 1"),
                _FakeHumanMessage("follow up 2"),
            ]
        )

        handler = MagicMock(return_value=_FakeModelResponse(content="response"))
        mw.wrap_model_call(request, handler)

        passed_request = handler.call_args[0][0]
        assert len(passed_request.messages) == 3
        assert passed_request.messages[0].content == "hello"
        assert passed_request.messages[2].content == "follow up 1\nfollow up 2"

    async def test_close(self):
        cls, _ = _import_middleware()
        mw = cls(delay=1.0)
        await mw.close()
        assert mw.debouncer.closed

    def test_debouncer_property(self):
        cls, _ = _import_middleware()
        from debouncer.core import Debouncer

        mw = cls(delay=2.0, max_wait=8.0)
        assert isinstance(mw.debouncer, Debouncer)
