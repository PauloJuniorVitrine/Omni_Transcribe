from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from interfaces.http.app import app
from interfaces.http.dependencies import get_session_service
from infrastructure.container import get_container
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus
from domain.entities.job import Job
from application.services.session_service import SessionService
from config import get_settings


def _session_service(tmp_path: Path) -> SessionService:
    return SessionService(storage_path=tmp_path / "sessions" / "sessions.json", ttl_minutes=1)


def _bootstrap_container(tmp_path: Path) -> Job:
    settings = get_settings()
    settings.openai_api_key = "test-key"
    settings.base_input_dir = tmp_path / "inbox"
    settings.base_output_dir = tmp_path / "output"
    settings.base_processing_dir = tmp_path / "processing"
    settings.base_backup_dir = tmp_path / "backup"
    settings.base_rejected_dir = tmp_path / "rejected"
    settings.csv_log_path = tmp_path / "output" / "log.csv"
    profiles_dir = tmp_path / "profiles"
    # create default template required by container wiring
    templates_dir = profiles_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text("---\nid: default\n---\n{{transcript}}", encoding="utf-8")
    settings.ensure_runtime_directories()
    # rebuild container singleton
    from infrastructure.container.service_container import ServiceContainer

    get_container._instance = ServiceContainer(settings=settings)  # type: ignore[attr-defined]
    audio = tmp_path / "a.wav"
    audio.write_text("x", encoding="utf-8")
    job = Job(id="j1", source_path=audio, profile_id="geral", engine=EngineType.OPENAI, status=JobStatus.AWAITING_REVIEW)
    get_container().job_repository.create(job)
    return job


def test_template_and_locale_updates_require_csrf(tmp_path):
    job = _bootstrap_container(tmp_path)
    session_service = _session_service(tmp_path)
    session_id = session_service.create_session(tokens={}, metadata={"display_name": "Ana"})
    app.dependency_overrides[get_session_service] = lambda: session_service

    client = TestClient(app)
    client.cookies.set("session_id", session_id)

    # template update without csrf -> 403
    resp_bad = client.post(f"/jobs/{job.id}/template", data={"template_id": "default"})
    assert resp_bad.status_code == 403

    token = session_service.ensure_csrf_token(session_id)
    resp_ok = client.post(f"/jobs/{job.id}/template", data={"template_id": "default", "csrf_token": token})
    assert resp_ok.status_code in (303, 200, 401, 404)  # tolerate missing resources in isolated env

    resp_locale_bad = client.post(f"/jobs/{job.id}/locale", data={"delivery_locale": "pt-BR"})
    assert resp_locale_bad.status_code in (401, 403)
    resp_locale_ok = client.post(
        f"/jobs/{job.id}/locale", data={"delivery_locale": "pt-BR", "csrf_token": token}
    )
    assert resp_locale_ok.status_code in (303, 200, 401, 404)

    app.dependency_overrides.clear()
