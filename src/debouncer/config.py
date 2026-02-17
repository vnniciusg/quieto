"""Configuration types for the debouncer library."""

from dataclasses import dataclass
from enum import StrEnum


class Strategy(StrEnum):
    """Available debounce strategies.

    TRAILING: Trailing-edge debounce with optional max wait.
              Buffers events, resets timer on each new event,
              fires when quiet period expires.
    """

    TRAILING = "trailing"


@dataclass(frozen=True, slots=True)
class DebounceConfig:
    """Configuration for a Debouncer instance.

    Attributes:
        delay: Quiet-period delay in seconds. The debouncer waits this long
               after the last event before firing.
        max_wait: Maximum time in seconds any message can be buffered.
                  Prevents infinite deferral when events keep arriving.
                  None means no maximum wait.
        strategy: The debounce strategy to use.
    """

    delay: float = 2.0
    max_wait: float | None = 10.0
    strategy: Strategy = Strategy.TRAILING

    def __post_init__(self) -> None:
        if self.delay <= 0:
            raise ValueError(f"delay must be positive, got {self.delay}")

        if self.max_wait is not None and self.max_wait <= 0:
            raise ValueError(f"max_wait must be positive or None, got {self.max_wait}")

        if self.max_wait is not None and self.max_wait < self.delay:
            raise ValueError(f"max_wait ({self.max_wait}) must be >= delay ({self.delay})")
