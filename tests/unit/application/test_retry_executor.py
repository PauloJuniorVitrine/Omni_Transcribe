from __future__ import annotations

import pytest

from application.services.retry import RetryConfig, RetryExecutor


def test_retry_executor_retries_with_exponential_backoff(monkeypatch):
    attempts = {"count": 0}
    delays: list[float] = []

    def flaky_call() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("temporary failure")
        return "ok"

    monkeypatch.setattr("application.services.retry.time.sleep", lambda seconds: delays.append(seconds))
    executor = RetryExecutor(RetryConfig(max_attempts=3, base_delay_seconds=0.1, factor=3))

    result = executor.run(flaky_call)

    assert result == "ok"
    assert delays == [0.1, 0.30000000000000004]
    assert attempts["count"] == 3


def test_retry_executor_raises_last_exception(monkeypatch):
    attempts = {"count": 0}

    def always_fail() -> None:
        attempts["count"] += 1
        raise ValueError("fatal")

    monkeypatch.setattr("application.services.retry.time.sleep", lambda seconds: None)
    executor = RetryExecutor(RetryConfig(max_attempts=2, base_delay_seconds=0.01))

    with pytest.raises(ValueError):
        executor.run(always_fail)

    assert attempts["count"] == 2


def test_retry_executor_zero_max_attempts_raises_assertion():
    executor = RetryExecutor(RetryConfig(max_attempts=0))

    with pytest.raises(AssertionError):
        executor.run(lambda: None)
