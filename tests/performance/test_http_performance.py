from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import interfaces.http.app as http_app
from interfaces.http.app import app, get_job_controller_dep, get_review_controller_dep
from interfaces.http.dependencies import require_active_session
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus
from tests.integration.test_http_api import StubJobController, StubJobRepository, StubReviewController


HTTP_ENDPOINTS = [
    ("/", "GET", 1.5, "main dashboard"),
    ("/jobs", "GET", 1.0, "job feed"),
    ("/jobs/job-perf", "GET", 1.2, "job detail"),
    ("/health", "GET", 0.7, "light health probe"),
]


def _perf_client(tmp_path: Path, monkeypatch) -> TestClient:
    job_repo = StubJobRepository(
        Job(
            id="job-perf",
            source_path=tmp_path / "audio.wav",
            profile_id="geral",
            engine=EngineType.OPENAI,
            status=JobStatus.AWAITING_REVIEW,
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
            "base_output_dir": tmp_path / "output",
            "base_backup_dir": tmp_path / "backup",
            "max_request_body_mb": 100,
            "max_audio_size_mb": 10,
            "profiles_dir": Path("profiles"),
            "openai_api_key": "test-key",
            "openai_chunk_trigger_mb": 1,
            "chatgpt_api_key": "test",
            "app_env": "test",
        },
    )()
    monkeypatch.setattr(http_app, "get_settings", lambda: fake_settings)
    http_app._app_settings = fake_settings  # type: ignore[attr-defined]
    monkeypatch.setattr(http_app, "_get_recent_incidents", lambda limit=5: [])
    client = TestClient(app)
    return client


@pytest.mark.performance
@pytest.mark.parametrize("path,method,threshold,description", HTTP_ENDPOINTS)
def test_http_endpoint_under_threshold(tmp_path, monkeypatch, path, method, threshold, description):
    client = _perf_client(tmp_path, monkeypatch)
    start = time.perf_counter()
    if method == "GET":
        resp = client.get(path)
    else:
        resp = client.post(path, data={})
    elapsed = time.perf_counter() - start
    assert resp.status_code < 500, f"{description} ({path}) falhou com HTTP {resp.status_code}"
    assert elapsed <= threshold, (
        f"{description} ({path}) demorou {elapsed:.3f}s acima do limite {threshold:.3f}s"
    )
    app.dependency_overrides.clear()
