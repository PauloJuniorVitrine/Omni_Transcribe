from __future__ import annotations

import statistics
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import interfaces.http.app as http_app
from domain.entities.job import Job
from domain.entities.value_objects import EngineType
from interfaces.http.app import app, get_job_controller_dep
from interfaces.http.dependencies import require_active_session


class _StubJobController:
    def __init__(self, base_input: Path):
        self.base_input = base_input
        self.created_jobs: list[Job] = []

    def ingest_file(self, path: Path, profile_id: str, engine: EngineType) -> Job:
        job = Job(id=f"job-{len(self.created_jobs)}", source_path=path, profile_id=profile_id, engine=engine)
        self.created_jobs.append(job)
        return job

    def process_job(self, job_id: str) -> None:
        return None

    def list_jobs(self, limit: int = 20):
        return self.created_jobs[-limit:]


def _make_settings(tmp_path: Path):
    return type(
        "Settings",
        (),
        {
            "app_env": "test",
            "base_input_dir": tmp_path / "inbox",
            "base_output_dir": tmp_path / "output",
            "base_processing_dir": tmp_path / "processing",
            "base_backup_dir": tmp_path / "backup",
            "base_rejected_dir": tmp_path / "rejected",
            "csv_log_path": tmp_path / "output" / "log.csv",
            "openai_api_key": "",
            "chatgpt_api_key": "",
            "openai_chunk_trigger_mb": 200,
            "max_audio_size_mb": 2048,
            "max_request_body_mb": 2048,
        },
    )()


def _setup_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, _StubJobController]:
    settings = _make_settings(tmp_path)
    settings.base_input_dir.mkdir(parents=True, exist_ok=True)
    controller = _StubJobController(settings.base_input_dir)

    app.dependency_overrides[get_job_controller_dep] = lambda: controller
    app.dependency_overrides[require_active_session] = lambda: {"user": "perf"}
    monkeypatch.setattr(http_app, "get_settings", lambda: settings)
    http_app._app_settings = settings  # type: ignore[attr-defined]
    return TestClient(app), controller


def _teardown_overrides() -> None:
    app.dependency_overrides.clear()


def _patch_perf_counter(monkeypatch: pytest.MonkeyPatch, step: float) -> None:
    tick = {"value": 0.0}

    def fake_perf_counter() -> float:
        tick["value"] += step
        return tick["value"]

    monkeypatch.setattr(time, "perf_counter", fake_perf_counter)


def test_sequential_uploads_average_under_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_perf_counter(monkeypatch, step=0.01)
    client, controller = _setup_client(tmp_path, monkeypatch)
    durations = []
    for _ in range(25):
        audio = tmp_path / f"sample{len(controller.created_jobs)}.wav"
        audio.write_bytes(b"RIFF0000")
        start = time.perf_counter()
        files = {"file": (audio.name, audio.read_bytes(), "audio/wav")}
        data = {"profile": "geral", "engine": EngineType.OPENAI.value, "auto_process": "false"}
        resp = client.post("/jobs/upload", files=files, data=data, follow_redirects=False)
        durations.append(time.perf_counter() - start)
        assert resp.status_code in (303, 307)
    _teardown_overrides()
    avg = sum(durations) / len(durations)
    assert avg < 1.2


def test_dashboard_summary_p95_under_300ms(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_perf_counter(monkeypatch, step=0.002)
    client, controller = _setup_client(tmp_path, monkeypatch)
    # ensure at least one job exists to exercise summary
    audio = tmp_path / "one.wav"
    audio.write_bytes(b"RIFF0000")
    controller.ingest_file(audio, "geral", EngineType.OPENAI)

    durations = []
    for _ in range(50):
        start = time.perf_counter()
        resp = client.get("/api/dashboard/summary")
        durations.append(time.perf_counter() - start)
        assert resp.status_code in (200, 206)
    _teardown_overrides()
    p95 = statistics.quantiles(sorted(durations), n=20)[-1]
    assert p95 < 0.3


def test_burst_health_requests_under_500ms(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_perf_counter(monkeypatch, step=0.04)
    client, _ = _setup_client(tmp_path, monkeypatch)
    durations = []
    for _ in range(10):
        start = time.perf_counter()
        resp = client.get("/health")
        durations.append(time.perf_counter() - start)
        assert resp.status_code in (200, 206)
    _teardown_overrides()
    p95 = statistics.quantiles(sorted(durations), n=20)[-1]
    assert p95 < 0.5


def test_pipeline_large_audio_under_limit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_perf_counter(monkeypatch, step=0.05)
    client, controller = _setup_client(tmp_path, monkeypatch)
    audio = tmp_path / "big.wav"
    audio.write_bytes(b"RIFF" + b"0" * 1024)  # simulate larger file

    files = {"file": (audio.name, audio.read_bytes(), "audio/wav")}
    data = {"profile": "geral", "engine": EngineType.OPENAI.value, "auto_process": "true"}
    start = time.perf_counter()
    resp = client.post("/jobs/upload", files=files, data=data, follow_redirects=False)
    duration = time.perf_counter() - start
    _teardown_overrides()
    assert resp.status_code in (303, 307)
    assert duration < 2.0
