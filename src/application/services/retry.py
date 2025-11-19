from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay_seconds: float = 2.0
    factor: float = 2.0


class RetryExecutor(Generic[T]):
    """Simple exponential backoff retry helper."""

    def __init__(self, config: RetryConfig | None = None) -> None:
        self.config = config or RetryConfig()

    def run(self, func: Callable[[], T]) -> T:
        attempts = 0
        delay = self.config.base_delay_seconds
        last_exc: Exception | None = None
        while attempts < self.config.max_attempts:
            try:
                return func()
            except Exception as exc:
                last_exc = exc
                attempts += 1
                if attempts >= self.config.max_attempts:
                    break
                time.sleep(delay)
                delay *= self.config.factor
        assert last_exc is not None
        raise last_exc
