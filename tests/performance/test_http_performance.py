from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

import interfaces.http.app as http_app
from interfaces.http.app import app, get_job_controller_dep, get_review_controller_dep
from interfaces.http.dependencies import require_active_session
from domain.entities.job import Job
from domain.entities.value_objects import EngineType
from tests.integration.test_http_api import (
    StubJobController,
    StubJobRepository,
    StubReviewController,
)


def test_http_endpoints_under_threshold(tmp_path, monkeypatch):
    job_repo = StubJobRepository(
        Job(
            id="job-perf",
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
        {"base_output_dir": Path("output"), "base_backup_dir": Path("backup"), "max_request_body_mb": 100},
    )()
    monkeypatch.setattr(http_app, "get_settings", lambda: fake_settings)
    http_app._app_settings = fake_settings  # type: ignore[attr-defined]
    monkeypatch.setattr(http_app, "_get_recent_incidents", lambda limit=5: [])

    tick = {"value": 0.0}

    def fake_perf_counter():
        tick["value"] += 0.001
        return tick["value"]

    monkeypatch.setattr(time, "perf_counter", fake_perf_counter)

    client = TestClient(app)
    iterations = 20
    start = time.perf_counter()
    for _ in range(iterations):
        client.get("/")
        client.get(f"/jobs/{job_repo.job.id}")
    total = time.perf_counter() - start
    avg = total / (iterations * 2)
    assert avg < 0.02, f"Tempo médio {avg:.4f}s excedeu 20ms"

    app.dependency_overrides.clear()
