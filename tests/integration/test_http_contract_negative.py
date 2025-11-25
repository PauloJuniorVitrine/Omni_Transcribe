from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from config import get_settings, reload_settings
from interfaces.http.app import app, get_job_controller_dep, get_job_log_service
from interfaces.http.dependencies import require_active_session
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus
from tests.integration.test_http_api import (
    _force_authentication,
    _override_app_settings,
    _build_download_query,
)  # type: ignore


@pytest.fixture(autouse=True)
def reset_overrides():
    yield
    app.dependency_overrides.clear()
    reload_settings()


def test_download_without_token_is_blocked(tmp_path, monkeypatch):
    # Prepara artefato no diretório permitido
    settings = get_settings()
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "sample.txt"
    artifact.write_text("conteudo", encoding="utf-8")

    # Força settings para apontar para tmp, e sessão ativa para bypass login/CSRF
    _force_authentication()
    _override_app_settings(
        monkeypatch,
        base_output_dir=output_dir,
        base_backup_dir=tmp_path / "backup",
        base_processing_dir=tmp_path / "processing",
    )

    client = TestClient(app)
    response = client.get(f"/artifacts?path={artifact}")
    assert response.status_code == 401
    assert "Token" in response.json()["detail"]


def test_download_with_expired_token_is_blocked(tmp_path, monkeypatch):
    # Prepara artefato e token expirado
    _force_authentication()
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "sample.txt"
    artifact.write_text("conteudo", encoding="utf-8")
    _override_app_settings(
        monkeypatch,
        base_output_dir=output_dir,
        base_backup_dir=tmp_path / "backup",
        base_processing_dir=tmp_path / "processing",
        webhook_secret="secret-expired",
    )

    # Constrói token expirado manualmente
    expired_params = _build_download_query(artifact, secret="secret-expired")
    expired_params["expires"] = "2000-01-01T00:00:00Z"
    client = TestClient(app)
    response = client.get("/artifacts", params={"path": str(artifact), **expired_params})
    assert response.status_code == 401
    assert "expirado" in response.json()["detail"].lower()


def test_upload_rejects_invalid_extension(tmp_path, monkeypatch):
    # Força dirs para o tmp e autenticação
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    _force_authentication()
    _override_app_settings(
        monkeypatch,
        base_input_dir=tmp_path / "inbox",
        base_output_dir=tmp_path / "output",
        base_processing_dir=tmp_path / "processing",
        base_backup_dir=tmp_path / "backup",
    )

    client = TestClient(app)
    files = {"file": ("malicioso.txt", b"invalido", "text/plain")}
    data = {"profile": "geral", "engine": "openai", "auto_process": "false", "csrf_token": "t"}
    resp = client.post("/jobs/upload", files=files, data=data)
    assert resp.status_code == 400
    assert "Extensao" in resp.json()["detail"]


def test_api_logs_require_session_even_with_valid_job(tmp_path, monkeypatch):
    # Reaproveita helper para criar job e log service, mas sem autenticação
    job = Job(
        id="job-logs-no-session-contract",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    from tests.integration.test_http_api import StubJobRepository, StubJobController, _make_log_service  # type: ignore

    repo = StubJobRepository(job)
    controller = StubJobController(repo)
    app.dependency_overrides[get_job_controller_dep] = lambda: controller
    app.dependency_overrides[get_job_log_service] = lambda: _make_log_service([])
    _override_app_settings(
        monkeypatch,
        base_input_dir=tmp_path / "inbox",
        base_output_dir=tmp_path / "output",
        base_processing_dir=tmp_path / "processing",
        base_backup_dir=tmp_path / "backup",
    )
    monkeypatch.setenv("TEST_MODE", "0")
    monkeypatch.setenv("OMNI_TEST_MODE", "0")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(f"/api/jobs/{job.id}/logs")
    assert response.status_code == 401


def test_cors_preflight_allows_origin(tmp_path, monkeypatch):
    _force_authentication()
    _override_app_settings(
        monkeypatch,
        base_input_dir=tmp_path / "inbox",
        base_output_dir=tmp_path / "output",
        base_processing_dir=tmp_path / "processing",
        base_backup_dir=tmp_path / "backup",
        cors_allowed_origins=["https://example.com"],
        cors_allowed_methods=["*"],
        cors_allowed_headers=["*"],
    )
    client = TestClient(app)
    response = client.options(
        "/api/dashboard/summary",
        headers={
            "origin": "https://example.com",
            "access-control-request-method": "GET",
            "access-control-request-headers": "content-type",
        },
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") in {"https://example.com", "*"}
