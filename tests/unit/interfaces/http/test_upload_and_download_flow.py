from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone
import hmac
from hashlib import sha256

from fastapi.testclient import TestClient

from interfaces.http.app import app
from interfaces.http.dependencies import require_active_session
from infrastructure.container import get_container
from domain.entities.value_objects import EngineType, ArtifactType
from config import get_settings


def _make_token(path: str, expires_iso: str) -> str:
    secret = get_settings().webhook_secret.encode("utf-8")
    payload = f"{path}:{expires_iso}".encode("utf-8")
    return hmac.new(secret, payload, sha256).hexdigest()


def test_upload_creates_job_and_download_requires_token(tmp_path, monkeypatch):
    app.dependency_overrides[require_active_session] = lambda: {}
    settings = get_settings()
    settings.openai_api_key = "test-key"
    settings.base_input_dir = tmp_path / "inbox"
    settings.base_output_dir = tmp_path / "output"
    settings.base_processing_dir = tmp_path / "processing"
    settings.base_backup_dir = tmp_path / "backup"
    settings.base_rejected_dir = tmp_path / "rejected"
    settings.csv_log_path = tmp_path / "output" / "log.csv"
    settings.ensure_runtime_directories()

    # fresh container for isolated dirs
    from infrastructure.container.service_container import ServiceContainer

    get_container._instance = ServiceContainer(settings=settings)  # type: ignore[attr-defined]

    client = TestClient(app)

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"RIFF0000")  # dummy
    files = {"file": ("sample.wav", audio_path.read_bytes(), "audio/wav")}
    data = {"profile": "geral", "engine": EngineType.OPENAI.value, "auto_process": "false"}
    resp = client.post("/jobs/upload", files=files, data=data, follow_redirects=False)
    assert resp.status_code in (303, 307)
    # find created job
    job_repo = get_container().job_repository
    jobs = job_repo.list_recent(1)
    assert jobs
    job = jobs[0]
    # simulate artifact file to allow download
    artifact_dir = Path(settings.base_output_dir) / job.id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact = artifact_dir / f"{job.id}_v{job.version}.txt"
    artifact.write_text("hello", encoding="utf-8")
    job.output_paths = {ArtifactType.TRANSCRIPT_TXT: artifact}

    # direct download should require token
    resp_bad = client.get("/artifacts", params={"path": artifact, "job_id": job.id})
    assert resp_bad.status_code in (401, 400, 404)

    expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    token = _make_token(str(artifact), expires)
    resp_ok = client.get("/artifacts", params={"path": artifact, "job_id": job.id, "token": token, "expires": expires})
    assert resp_ok.status_code == 200
    assert resp_ok.content == artifact.read_bytes()
    app.dependency_overrides.clear()


def test_upload_rejects_when_exceeds_limit(tmp_path, monkeypatch):
    app.dependency_overrides[require_active_session] = lambda: {}
    settings = get_settings()
    settings.openai_api_key = "test-key"
    settings.base_input_dir = tmp_path / "inbox"
    settings.base_output_dir = tmp_path / "output"
    settings.base_processing_dir = tmp_path / "processing"
    settings.base_backup_dir = tmp_path / "backup"
    settings.base_rejected_dir = tmp_path / "rejected"
    settings.csv_log_path = tmp_path / "output" / "log.csv"
    settings.max_audio_size_mb = 1  # 1MB hard limit for test
    settings.ensure_runtime_directories()

    from infrastructure.container.service_container import ServiceContainer

    get_container._instance = ServiceContainer(settings=settings)  # type: ignore[attr-defined]

    client = TestClient(app)
    payload = b"x" * (settings.max_audio_size_mb * 1024 * 1024 + 512)
    files = {"file": ("big.wav", payload, "audio/wav")}
    data = {"profile": "geral", "engine": EngineType.OPENAI.value, "auto_process": "false"}

    resp = client.post("/jobs/upload", files=files, data=data)
    assert resp.status_code in {400, 413}
    detail = (resp.json().get("detail") or "").lower()
    assert "limite" in detail
    saved = Path(settings.base_input_dir) / "geral" / "big.wav"
    assert not saved.exists()
    assert get_container().job_repository.list_recent(1) == []
    app.dependency_overrides.clear()
