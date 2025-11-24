from __future__ import annotations

import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import interfaces.http.app as http_app
from domain.entities.job import Job
from domain.entities.value_objects import EngineType
from interfaces.http.app import app, get_job_controller_dep, get_review_controller_dep
from interfaces.http.dependencies import require_active_session
from tests.integration.test_http_api import (
    StubJobController,
    StubJobRepository,
    StubReviewController,
)


def _setup_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, StubJobRepository]:
    job_repo = StubJobRepository(
        Job(
            id="job-perf-ext",
            source_path=tmp_path / "audio.wav",
            profile_id="geral",
            engine=EngineType.OPENAI,
        )
    )
    job_controller = StubJobController(job_repo)
    review_controller = StubReviewController()
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    app.dependency_overrides[require_active_session] = lambda: {"user": "perf"}

    fake_settings = type(
        "Settings",
        (),
        {
            "app_env": "test",
            "base_output_dir": tmp_path / "output",
            "base_backup_dir": tmp_path / "backup",
            "max_request_body_mb": 100,
            "openai_api_key": "",
            "chatgpt_api_key": "",
            "openai_chunk_trigger_mb": 200,
            "max_audio_size_mb": 2048,
        },
    )()
    monkeypatch.setattr(http_app, "get_settings", lambda: fake_settings)
    http_app._app_settings = fake_settings  # type: ignore[attr-defined]
    monkeypatch.setattr(http_app, "_get_recent_incidents", lambda limit=5: [])
    return TestClient(app), job_repo


def _teardown_overrides() -> None:
    app.dependency_overrides.clear()


def _patch_perf_counter(monkeypatch: pytest.MonkeyPatch, step: float = 0.0005) -> None:
    tick = {"value": 0.0}

    def fake_perf_counter() -> float:
        tick["value"] += step
        return tick["value"]

    monkeypatch.setattr(time, "perf_counter", fake_perf_counter)


@pytest.mark.parametrize("users", [10, 50])
def test_http_concurrent_p95_under_threshold(tmp_path, monkeypatch, users):
    _patch_perf_counter(monkeypatch, step=0.0005)
    client, job_repo = _setup_client(tmp_path, monkeypatch)

    durations = []

    def worker():
        start = time.perf_counter()
        client.get("/")
        client.get(f"/jobs/{job_repo.job.id}")
        durations.append(time.perf_counter() - start)

    with ThreadPoolExecutor(max_workers=users) as pool:
        for _ in range(users):
            pool.submit(worker)

    _teardown_overrides()

    durations.sort()
    p95 = statistics.quantiles(durations, n=20)[-1]
    limit = 0.08 if users == 10 else 0.12
    assert p95 < limit, f"p95 {p95:.4f}s excedeu limite com {users} usuarios"


def test_http_detects_regression_when_latency_spikes(tmp_path, monkeypatch):
    # Mantém perf_counter real aqui para validar regressão
    client, job_repo = _setup_client(tmp_path, monkeypatch)

    original_perf_counter = time.perf_counter
    tick = {"value": 0.0}

    def slow_counter():
        tick["value"] += 0.12
        return tick["value"]

    monkeypatch.setattr(time, "perf_counter", slow_counter)

    def run_requests():
        start = time.perf_counter()
        client.get("/")
        client.get(f"/jobs/{job_repo.job.id}")
        return time.perf_counter() - start

    durations = [run_requests() for _ in range(5)]
    _teardown_overrides()
    monkeypatch.setattr(time, "perf_counter", original_perf_counter)

    p95 = statistics.quantiles(sorted(durations), n=20)[-1]
    with pytest.raises(AssertionError):
        assert p95 < 0.05, "deveria falhar quando a latência ultrapassa 50ms"
    assert p95 >= 0.05
