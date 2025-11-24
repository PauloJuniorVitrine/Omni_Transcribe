from __future__ import annotations

import hmac
import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import interfaces.http.app as http_app
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus
from interfaces.http.app import app, get_job_controller_dep
from interfaces.http.dependencies import require_active_session


class _Repo:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}

    def create(self, job: Job) -> Job:
        self.jobs[job.id] = job
        return job

    def list_recent(self, limit: int = 20):
        return list(self.jobs.values())[-limit:]

    def find_by_id(self, job_id: str):
        return self.jobs.get(job_id)


class _JobController:
    def __init__(self, repo: _Repo):
        self.job_repository = repo

    def list_jobs(self, limit: int = 20):
        return self.job_repository.list_recent(limit)

    def ingest_file(self, path: Path, profile_id: str, engine: EngineType) -> Job:
        job = Job(id=f"job-{len(self.job_repository.jobs)}", source_path=path, profile_id=profile_id, engine=engine)
        job.metadata = {"source_folder": path.parent.name}
        self.job_repository.create(job)
        return job

    def process_job(self, job_id: str) -> None:
        job = self.job_repository.find_by_id(job_id)
        if job:
            job.set_status(JobStatus.ASR_COMPLETED)


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
            "webhook_secret": "changeme",
        },
    )()


@pytest.fixture
def e2e_client(tmp_path, monkeypatch):
    settings = _make_settings(tmp_path)
    settings.base_input_dir.mkdir(parents=True, exist_ok=True)
    repo = _Repo()
    controller = _JobController(repo)
    app.dependency_overrides[get_job_controller_dep] = lambda: controller
    app.dependency_overrides[require_active_session] = lambda: {"user": "e2e"}
    monkeypatch.setattr(http_app, "get_settings", lambda: settings)
    http_app._app_settings = settings  # type: ignore[attr-defined]
    client = TestClient(app)
    yield client, repo, settings
    app.dependency_overrides.clear()


def test_e2e_upload_to_summary_and_job_detail(e2e_client):
    client, repo, settings = e2e_client
    audio = settings.base_input_dir / "geral" / "sample.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"RIFF0000")

    files = {"file": ("sample.wav", audio.read_bytes(), "audio/wav")}
    data = {"profile": "geral", "engine": EngineType.OPENAI.value, "auto_process": "false"}
    resp = client.post("/jobs/upload", files=files, data=data, follow_redirects=False)
    assert resp.status_code in (303, 307)

    jobs = repo.list_recent()
    assert len(jobs) == 1
    job = jobs[0]
    assert job.metadata.get("source_folder") == "geral"

    summary = client.get("/api/dashboard/summary")
    assert summary.status_code in (200, 206)
    assert summary.json()["summary"]["total"] == 1

    detail = client.get(f"/jobs/{job.id}")
    assert detail.status_code == 200


def test_e2e_webhook_signature_valid_and_invalid(e2e_client):
    client, _repo, settings = e2e_client
    payload = b"body"
    sig = hmac.new(settings.webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    ok = client.post(
        "/webhooks/external",
        content=payload,
        headers={"X-Signature": sig, "X-Signature-Timestamp": "1", "X-Integration-Id": "external"},
    )
    assert ok.status_code == 200
    bad = client.post("/webhooks/external", content=payload)
    assert bad.status_code == 401
