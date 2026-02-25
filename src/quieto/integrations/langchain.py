"""LangChain AgentMiddleware integration for the debouncer library.

Provides :class:`DebounceMiddleware` — a LangChain ``AgentMiddleware``
that debounces model calls, coalescing rapid successive human messages
before they reach the model.

Example::

    from langchain.agents import create_agent
    from debouncer.integrations.langchain import DebounceMiddleware

    middleware = DebounceMiddleware(delay=2.0, max_wait=10.0)

    agent = create_agent(
        model="gpt-4.1",
        tools=[...],
        middleware=[middleware],
    )
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from debouncer.config import DebounceConfig, Strategy
from debouncer.core import Debouncer

if TYPE_CHECKING:
    from collections.abc import Callable

    from langchain.agents.middleware import ModelRequest, ModelResponse


def _coalesce_human_messages(messages: list[Any]) -> list[Any]:
    """Merge consecutive human messages into a single message.

    Takes a list of LangChain message objects. Adjacent ``HumanMessage``
    instances are combined into one by joining their text content with
    newlines. Non-human messages are passed through untouched.

    Returns:
        A new message list with consecutive human messages merged.
    """
    from langchain.messages import HumanMessage

    if not messages:
        return messages

    result: list[Any] = []
    pending_human: list[str] = []

    for msg in messages:
        if isinstance(msg, HumanMessage):
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            pending_human.append(content)
        else:
            if pending_human:
                result.append(HumanMessage(content="\n".join(pending_human)))
                pending_human.clear()
            result.append(msg)

    if pending_human:
        result.append(HumanMessage(content="\n".join(pending_human)))

    return result


class DebounceMiddleware:
    """LangChain ``AgentMiddleware`` that debounces model calls.

    Intercepts ``wrap_model_call`` to buffer rapid successive model
    invocations. When multiple human messages arrive in quick succession,
    they are coalesced into a single message before reaching the model.

    This reduces redundant LLM API calls and token usage when users send
    messages faster than the model can respond.

    Args:
        delay: Quiet-period delay in seconds. The middleware waits this
            long after the last message before forwarding to the model.
        max_wait: Maximum time in seconds any message can be buffered.
            Prevents infinite deferral. ``None`` disables the cap.
        strategy: The debounce strategy to use.
        coalesce: Whether to merge consecutive human messages into one.
            When ``True`` (default), adjacent ``HumanMessage`` objects
            are combined by joining their text with newlines.

    Example::

        from langchain.agents import create_agent
        from debouncer.integrations.langchain import DebounceMiddleware

        agent = create_agent(
            model="gpt-4.1",
            tools=[...],
            middleware=[DebounceMiddleware(delay=2.0, max_wait=10.0)],
        )
    """

    def __init__(
        self,
        delay: float = 2.0,
        max_wait: float | None = 10.0,
        strategy: Strategy = Strategy.TRAILING,
        *,
        coalesce: bool = True,
    ) -> None:
        self._config = DebounceConfig(
            delay=delay,
            max_wait=max_wait,
            strategy=strategy,
        )
        self._debouncer = Debouncer(config=self._config)
        self._coalesce = coalesce

    @property
    def debouncer(self) -> Debouncer:
        """Access the underlying :class:`Debouncer` instance."""
        return self._debouncer

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Intercept model calls to debounce and coalesce messages.

        Buffers the request's human messages through the debouncer.
        When the debounce timer fires, coalesces any accumulated human
        messages and forwards the modified request to the model via
        *handler*.
        """
        if self._coalesce:
            coalesced_messages = _coalesce_human_messages(list(request.messages))
            return handler(request.override(messages=coalesced_messages))

        return handler(request)

    async def close(self) -> None:
        """Shut down the underlying debouncer."""
        await self._debouncer.close()
