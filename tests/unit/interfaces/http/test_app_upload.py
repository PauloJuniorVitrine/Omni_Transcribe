from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import interfaces.http.app as http_app
from interfaces.http.app import app, get_job_controller_dep
from interfaces.http.dependencies import require_active_session
from tests.integration.test_http_api import StubJobControllerUpload


def _setup_upload_client(monkeypatch, tmp_path: Path):
    job_controller = StubJobControllerUpload()
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[require_active_session] = lambda: {"user": "perf"}
    settings = SimpleNamespace(
        app_env="test",
        max_audio_size_mb=1,
        base_input_dir=tmp_path,
        max_request_body_mb=1,
    )
    monkeypatch.setattr(http_app, "get_settings", lambda: settings)
    http_app._app_settings = settings  # type: ignore[attr-defined]
    job_controller.job_repository = SimpleNamespace(find_by_id=lambda job_id: job_controller.job)
    client = TestClient(app)
    return client, job_controller


async def _fake_persist(tmp_path: Path, total_bytes: int):
    path = tmp_path / "upload.wav"
    path.write_bytes(b"audio")
    return path, total_bytes


@pytest.mark.parametrize("total_bytes", [0, 1024])
def test_upload_job_handles_total_read(monkeypatch, tmp_path: Path, total_bytes):
    client, job_controller = _setup_upload_client(monkeypatch, tmp_path)
    async def fake(file, profile, max_bytes):
        return await _fake_persist(tmp_path, total_bytes)

    monkeypatch.setattr(http_app, "_persist_upload_file", fake)
    response = client.post(
        "/jobs/upload",
        data={"profile": "geral", "engine": "openai", "auto_process": "false"},
        files={"file": ("audio.wav", b"123", "audio/wav")},
        follow_redirects=False,
    )

    if total_bytes == 0:
        assert response.status_code == 400
        assert job_controller.job is None
    else:
        assert response.status_code == 303
        assert "flash=process-started" in response.headers["location"] or "flash=upload-success" in response.headers["location"]


def test_upload_job_auto_process_error(monkeypatch, tmp_path: Path):
    client, job_controller = _setup_upload_client(monkeypatch, tmp_path)

    async def fake(file, profile, max_bytes):
        path = tmp_path / "upload.wav"
        path.write_bytes(b"audio")
        return path, 1024

    def process_job(job_id: str) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(http_app, "_persist_upload_file", fake)
    monkeypatch.setattr(job_controller, "process_job", process_job)
    response = client.post(
        "/jobs/upload",
        data={"profile": "geral", "engine": "openai", "auto_process": "true"},
        files={"file": ("audio.wav", b"123", "audio/wav")},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("flash=process-error")


def test_api_upload_job_handles_zero_bytes(monkeypatch, tmp_path: Path):
    client, job_controller = _setup_upload_client(monkeypatch, tmp_path)

    async def fake(file, profile, max_bytes):
        path = tmp_path / "upload.wav"
        path.write_bytes(b"audio")
        return path, 0

    monkeypatch.setattr(http_app, "_persist_upload_file", fake)
    monkeypatch.setattr(http_app, "_validate_upload_token", lambda *args, **kwargs: None)

    response = client.post(
        "/api/uploads",
        data={"token": "token", "expires": "now", "profile": "geral", "engine": "openai"},
        files={"file": ("audio.wav", b"123", "audio/wav")},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "Arquivo vazio" in response.json()["detail"]


def test_api_upload_job_auto_process_failure(monkeypatch, tmp_path: Path):
    client, job_controller = _setup_upload_client(monkeypatch, tmp_path)

    async def fake(file, profile, max_bytes):
        path = tmp_path / "upload.wav"
        path.write_bytes(b"audio")
        return path, 1024

    def process_job(job_id: str) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(http_app, "_persist_upload_file", fake)
    monkeypatch.setattr(http_app, "_validate_upload_token", lambda *args, **kwargs: None)
    monkeypatch.setattr(job_controller, "process_job", process_job)

    response = client.post(
        "/api/uploads",
        data={"token": "token", "expires": "now", "profile": "geral", "engine": "openai", "auto_process": "true"},
        files={"file": ("audio.wav", b"123", "audio/wav")},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "boom" in response.json()["detail"]
