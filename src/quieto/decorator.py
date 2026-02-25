"""Decorator API for applying debounce behavior to async functions."""

import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, NamedTuple, TypeVar, cast, overload

from debouncer.config import DebounceConfig, Strategy
from debouncer.core import Debouncer

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class ExtractedMessage(NamedTuple):
    """Result of extracting the message from function arguments."""

    message: Any
    remaining_args: tuple[Any, ...]
    remaining_kwargs: dict[str, Any]


def _extract_message(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> ExtractedMessage:
    if args:
        return ExtractedMessage(args[0], args[1:], kwargs)
    if "message" in kwargs:
        new_kwargs = dict(kwargs)
        message = new_kwargs.pop("message")
        return ExtractedMessage(message, (), new_kwargs)
    raise TypeError("Missing message argument")


@overload
def debounce(
    func: F,
    /,
) -> F: ...


@overload
def debounce(
    *,
    delay: float = 2.0,
    max_wait: float | None = 10.0,
    strategy: Strategy = Strategy.TRAILING,
) -> Callable[[F], F]: ...


def debounce(
    func: F | None = None,
    /,
    *,
    delay: float = 2.0,
    max_wait: float | None = 10.0,
    strategy: Strategy = Strategy.TRAILING,
) -> F | Callable[[F], F]:
    """Decorator that debounces calls to a function.

    The decorated function's signature changes: instead of being called with
    its normal arguments, each call pushes a single message into the debouncer.
    When the debounce timer fires, the original function is invoked with the
    full list of coalesced messages.

    The original function must accept a ``list[str]`` as its first positional argument.

    Args:
        func: The function to decorate (when used without parentheses).
        delay: Quiet-period delay in seconds.
        max_wait: Maximum buffering time in seconds, or None for no limit.
        strategy: The debounce strategy to use.

    Examples:
    ```python
        # With parentheses
        @debounce(delay=1.0)
        async def handler(messages: list[str]) -> None:
            print(messages)

        # Without parentheses (uses defaults)
        @debounce
        async def handler(messages: list[str]) -> None:
            print(messages)
    ```
    """
    config = DebounceConfig(delay=delay, max_wait=max_wait, strategy=strategy)

    def decorator(fn: F) -> F:
        if not inspect.iscoroutinefunction(fn):
            raise TypeError("@debounce only supports async function.")

        debouncer = Debouncer(config=config)

        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            extracted = _extract_message(args, kwargs)
            await debouncer.push(extracted.message)
            batch = await debouncer.next_batch()
            return await fn(batch, *extracted.remaining_args, **extracted.remaining_kwargs)

        wrapper.debouncer = debouncer  # type: ignore[attr-defined]
        wrapper.flush = debouncer.flush  # type: ignore[attr-defined]
        wrapper.close = debouncer.close  # type: ignore[attr-defined]

        return cast("F", wrapper)

    if func is not None:
        return decorator(func)

    return decorator
