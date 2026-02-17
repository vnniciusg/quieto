# debouncer

High-performance async debounce library for Python 3.13+ with message coalescing, designed for LLM-powered applications.

> **Built with [Claude Code](https://claude.ai/claude-code)** — this entire codebase (architecture, implementation, tests, and this README) was written by Claude via Claude Code.

## The problem

When users interact with LLM-powered apps, they often send messages in quick succession:

```
t=0.0s  User: "hi"
t=2.0s  User: "everything ok?"
```

Without debouncing, this triggers **2 separate LLM API calls**. With debouncing, both messages are coalesced into **1 call**:

```
LLM receives: ["hi", "everything ok?"]
```

## Install

```bash
uv add debouncer
```

With LangChain integration:

```bash
uv add debouncer[langchain]
```

Or with pip:

```bash
pip install debouncer
```

## Quick start

### Decorator API

```python
from debouncer import debounce

@debounce(delay=2.0, max_wait=10.0)
async def handle(messages: list[str]) -> str:
    return await llm.invoke("\n".join(messages))

# Each call pushes a message; the function fires after 2s of quiet
await handle("hi")
await handle("everything ok?")
# -> handle is called once with ["hi", "everything ok?"]
```

### Imperative API

```python
from debouncer import Debouncer, DebounceConfig

async with Debouncer(config=DebounceConfig(delay=2.0, max_wait=10.0)) as d:
    await d.push("hello")
    await d.push("world")
    batch = await d.next_batch()  # ["hello", "world"]
```

### Async iterator

```python
async for batch in debouncer.batches():
    response = await llm.invoke(batch)
```

## Strategies

| Strategy | Enum | Description |
|----------|------|-------------|
| **Trailing** | `Strategy.TRAILING` | Default. Resets timer on each message, `max_wait` caps total buffering time. |
| **Adaptive** | `Strategy.ADAPTIVE` | Learns from user behavior via EMA. Fast typists get shorter delays. |
| **Actor** | `Strategy.ACTOR` | Queue-based with natural backpressure via `asyncio.Queue`. |

```python
from debouncer import Debouncer, DebounceConfig, Strategy

d = Debouncer(config=DebounceConfig(
    delay=2.0,
    max_wait=10.0,
    strategy=Strategy.ADAPTIVE,
))
```

## Session manager

Independent debounce state per user/session:

```python
from debouncer import SessionManager

async with SessionManager(delay=2.0, max_wait=10.0) as mgr:
    await mgr.push("session-123", "hi")
    await mgr.push("session-123", "everything ok?")
    await mgr.push("session-456", "different user")

    batch_123 = await mgr.next_batch("session-123")  # ["hi", "everything ok?"]
    batch_456 = await mgr.next_batch("session-456")  # ["different user"]
```

Idle sessions are garbage-collected automatically.

## LangChain middleware

```python
from langchain.agents import create_agent
from debouncer.integrations.langchain import DebounceMiddleware

agent = create_agent(
    model="gpt-4.1",
    tools=[...],
    middleware=[DebounceMiddleware(delay=2.0, max_wait=10.0)],
)
```

The middleware implements `wrap_model_call` to coalesce consecutive `HumanMessage` objects before they reach the model. Disable coalescing with `coalesce=False`.

## API reference

### `DebounceConfig`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `delay` | `float` | `2.0` | Quiet-period delay in seconds |
| `max_wait` | `float \| None` | `10.0` | Max buffering time. `None` = no limit |
| `strategy` | `Strategy` | `TRAILING` | Debounce strategy |

### `Debouncer`

| Method | Description |
|--------|-------------|
| `push(message)` | Add a message to the buffer |
| `next_batch()` | Await the next flushed batch |
| `flush()` | Force-flush immediately |
| `close()` | Close and flush pending messages |
| `batches()` | Async iterator over batches |
| `delay` | Get/set the delay (validates against `max_wait`) |

### `@debounce`

```python
@debounce                          # defaults: delay=2.0, max_wait=10.0
@debounce(delay=1.0, max_wait=5.0) # custom config

# wrapper attributes:
handler.debouncer  # access the Debouncer instance
handler.flush()    # force-flush
await handler.close()  # shut down
```

## Development

```bash
# Install dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/ -v

# Run tests with coverage
uv run pytest tests/ -v --cov=src --cov-report=term

# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Type check
uv run mypy src/
```

## License

[MIT](LICENSE)
