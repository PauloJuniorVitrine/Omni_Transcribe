from __future__ import annotations

import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tests.performance.test_http_performance_extended import (
    _patch_perf_counter,
    _setup_client,
    _teardown_overrides,
)


def test_http_burst_home_and_health_under_threshold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_perf_counter(monkeypatch, step=0.0004)
    client, _ = _setup_client(tmp_path, monkeypatch)

    durations = []
    for _ in range(30):
        start = time.perf_counter()
        client.get("/")
        client.get("/health")
        durations.append(time.perf_counter() - start)

    _teardown_overrides()
    p95 = statistics.quantiles(sorted(durations), n=20)[-1]
    assert p95 < 0.05, f"p95 {p95:.4f}s excedeu limite para burst home/health"


@pytest.mark.parametrize("users,limit", [(5, 0.05), (20, 0.1)])
def test_job_detail_concurrent_requests_under_threshold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, users: int, limit: float
) -> None:
    _patch_perf_counter(monkeypatch, step=0.0005)
    client, job_repo = _setup_client(tmp_path, monkeypatch)

    durations = []

    def worker() -> None:
        start = time.perf_counter()
        client.get(f"/jobs/{job_repo.job.id}")
        durations.append(time.perf_counter() - start)

    with ThreadPoolExecutor(max_workers=users) as pool:
        for _ in range(users):
            pool.submit(worker)

    _teardown_overrides()
    p95 = statistics.quantiles(sorted(durations), n=20)[-1]
    assert p95 < limit, f"p95 {p95:.4f}s excedeu limite com {users} usuarios"
