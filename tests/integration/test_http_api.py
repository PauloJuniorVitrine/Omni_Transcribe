from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import config
from config import profile_loader
from config.runtime_credentials import RuntimeCredentialStore
from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus, LogLevel
from domain.entities.transcription import TranscriptionResult, Segment, PostEditResult
from application.services.job_log_service import JobLogService, JobLogQueryResult
from application.services.accuracy_service import TranscriptionAccuracyGuard
from domain.usecases.pipeline import ProcessJobPipeline
import interfaces.http.app as http_app
from interfaces.http.app import (
    app,
    get_job_controller_dep,
    get_job_log_service,
    get_review_controller_dep,
)
from interfaces.http.dependencies import require_active_session
import inspect

print("interfaces.http.app loaded from", http_app.__file__)
print("job_detail source on import:\n", inspect.getsource(http_app.job_detail))

class StubJobRepository:
    def __init__(self, jobs: Job | list[Job]) -> None:
        if isinstance(jobs, list):
            self.jobs = jobs
        else:
            self.jobs = [jobs]
        self.job = self.jobs[0] if self.jobs else None

    def find_by_id(self, job_id: str) -> Job | None:
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None

    def list_recent(self, limit: int = 20):
        return self.jobs[:limit]

    def update(self, job: Job) -> Job:
        for index, existing in enumerate(self.jobs):
            if existing.id == job.id:
                self.jobs[index] = job
                break
        else:
            self.jobs.append(job)
        self.job = job
        return job


class StubJobController:
    def __init__(self, repository: StubJobRepository) -> None:
        self.job_repository = repository
        self.processed: list[str] = []

    def list_jobs(self, limit: int = 20, page: int = 1):
        jobs = self.job_repository.list_recent(limit * page)
        start = (page - 1) * limit
        return jobs[start : start + limit], False

    def process_job(self, job_id: str) -> None:
        self.processed.append(job_id)


class StubJobControllerUpload:
    def __init__(self) -> None:
        self.job = None
        self.processed: list[str] = []

    def ingest_file(self, path: Path, profile_id: str, engine: EngineType) -> Job:
        self.job = Job(
            id="job-upload",
            source_path=path,
            profile_id=profile_id,
            engine=engine,
            status=JobStatus.PENDING,
        )
        return self.job

    def process_job(self, job_id: str) -> None:
        self.processed.append(job_id)

    def list_jobs(self, limit: int = 20):
        return [self.job] if self.job else []


class StubReviewController:
    def __init__(self) -> None:
        self.decisions: list[tuple[str, bool, str | None]] = []

    def submit_review(self, job_id: str, reviewer: str, approved: bool, notes: str | None = None) -> Job:
        self.decisions.append((job_id, approved, notes))
        return Job(
            id=job_id,
            source_path=Path("inbox/file.wav"),
            profile_id="geral",
            engine=EngineType.OPENAI,
            status=JobStatus.APPROVED if approved else JobStatus.ADJUSTMENTS_REQUIRED,
        )


class StubIncidentLogRepository:
    def __init__(self, entries: list[LogEntry]) -> None:
        self.entries = entries

    def list_recent(self, limit: int = 5):
        return self.entries[:limit]


class StubLogRepository:
    def __init__(self, entries: list[LogEntry]) -> None:
        self.entries = entries

    def append(self, entry: LogEntry) -> None:
        self.entries.append(entry)

    def list_by_job(self, job_id: str) -> list[LogEntry]:
        return [entry for entry in self.entries if entry.job_id == job_id]


def _make_log_service(entries: list[LogEntry]) -> JobLogService:
    return JobLogService(StubLogRepository(entries))


def test_http_routes_list_detail_review_and_artifact(tmp_path, monkeypatch):
    job = Job(
        id="job-http",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    review_controller = StubReviewController()

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    artifact_path = output_dir / job.id / f"{job.id}_v1.txt"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("conteudo", encoding="utf-8")
    job.output_paths[ArtifactType.TRANSCRIPT_TXT] = artifact_path

    client = TestClient(app)

    response = client.get("/")
    assert response.status_code == 200, response.text
    assert job.id in response.text

    detail = client.get(f"/jobs/{job.id}")
    assert detail.status_code == 200, detail.text
    assert job.source_path.name in detail.text

    process = client.post(f"/api/jobs/{job.id}/process")
    assert process.status_code == 200, process.text
    assert job.id in job_controller.processed

    params = _build_download_query(artifact_path)
    artifact = client.get("/artifacts", params={"path": str(artifact_path), **params})
    assert artifact.status_code == 200, artifact.text
    assert artifact.content == b"conteudo"

    invalid_params = _build_download_query(tmp_path / "missing.txt")
    invalid = client.get(
        "/artifacts",
        params={"path": str(tmp_path / "missing.txt"), "job_id": job.id, **invalid_params},
        headers={"accept": "text/html"},
        follow_redirects=False,
    )
    assert invalid.status_code == 303
    assert invalid.headers["location"].endswith("flash=download-error")

    app.dependency_overrides.clear()


def test_ui_process_job_sets_flash(tmp_path, monkeypatch):
    job = Job(
        id="job-process-ui",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app, follow_redirects=False)
    response = client.post(f"/jobs/{job.id}/process")
    assert response.status_code == 303
    assert response.headers["location"].endswith("flash=process-started")
    assert job.id in job_controller.processed

    app.dependency_overrides.clear()


def test_ui_process_job_handles_failure(tmp_path, monkeypatch):
    job = Job(
        id="job-process-error",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)

    def _fail(job_id: str) -> None:
        raise RuntimeError("boom")

    job_controller.process_job = _fail  # type: ignore[assignment]
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app, follow_redirects=False)
    response = client.post(f"/jobs/{job.id}/process")
    assert response.status_code == 303
    assert response.headers["location"].endswith("flash=process-error")

    app.dependency_overrides.clear()


def test_upload_creates_job_and_saves_file(tmp_path, monkeypatch):
    controller = StubJobControllerUpload()
    app.dependency_overrides[get_job_controller_dep] = lambda: controller
    _force_authentication()
    _override_app_settings(monkeypatch, base_input_dir=tmp_path)

    client = TestClient(app, follow_redirects=False)
    files = {"file": ("audio.wav", b"data", "audio/wav")}
    data = {"profile": "geral", "engine": "openai", "auto_process": "true", "csrf_token": "test-csrf"}
    response = client.post("/jobs/upload", files=files, data=data)
    assert response.status_code == 303
    assert controller.job is not None
    assert controller.job.source_path.exists()
    assert controller.processed == ["job-upload"]

    app.dependency_overrides.clear()


def test_api_upload_with_token(tmp_path, monkeypatch):
    controller = StubJobControllerUpload()
    app.dependency_overrides[get_job_controller_dep] = lambda: controller
    _force_authentication()
    _override_app_settings(monkeypatch, base_input_dir=tmp_path, webhook_secret="secret")
    client = TestClient(app)
    token_response = client.get("/api/uploads/token?profile=geral&engine=openai")
    assert token_response.status_code == 200
    token_payload = token_response.json()
    files = {"file": ("api.wav", b"data", "audio/wav")}
    data = {
        "token": token_payload["token"],
        "expires": token_payload["expires"],
        "profile": token_payload["profile"],
        "engine": token_payload["engine"],
    }
    response = client.post("/api/uploads", files=files, data=data)
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == controller.job.id
    assert body["auto_processed"] is False
    app.dependency_overrides.clear()


def test_upload_auto_process_updates_accuracy_metadata(tmp_path, monkeypatch):
    class StubJobControllerUploadAccuracy:
        def __init__(self) -> None:
            self.job = None
            self.processed: list[str] = []

        def ingest_file(self, path: Path, profile_id: str, engine: EngineType) -> Job:
            self.job = Job(
                id="job-upload-acc",
                source_path=path,
                profile_id=profile_id,
                engine=engine,
                status=JobStatus.PENDING,
            )
            return self.job

        def process_job(self, job_id: str) -> None:
            if not self.job:
                raise RuntimeError("no job")
            self.job.metadata["accuracy_status"] = "needs_review"
            self.processed.append(job_id)

        def list_jobs(self, limit: int = 20):
            return [self.job] if self.job else []

    controller = StubJobControllerUploadAccuracy()
    app.dependency_overrides[get_job_controller_dep] = lambda: controller
    _force_authentication()
    _override_app_settings(monkeypatch, base_input_dir=tmp_path)

    client = TestClient(app, follow_redirects=False)
    files = {"file": ("audio.wav", b"data", "audio/wav")}
    data = {"profile": "geral", "engine": "openai", "auto_process": "true", "csrf_token": "test-csrf"}
    response = client.post("/jobs/upload", files=files, data=data)
    assert response.status_code == 303
    assert controller.job is not None
    assert controller.job.metadata.get("accuracy_status") == "needs_review"
    assert controller.processed == ["job-upload-acc"]

    app.dependency_overrides.clear()


def test_process_job_handles_accuracy_guard_error(tmp_path, monkeypatch):
    job = Job(
        id="job-acc-error",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    error_message = "accuracy-too-low"

    class Controller(StubJobController):
        def process_job(self, job_id: str) -> None:
            raise RuntimeError(error_message)

    job_controller = Controller(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(f"/api/jobs/{job.id}/process")
    assert response.status_code == 400
    assert error_message in response.json()["detail"]

    app.dependency_overrides.clear()


def test_api_process_job_runs_accuracy_guard(tmp_path, monkeypatch):
    job = Job(
        id="job-acc-guard",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )

    class GuardJobRepo(StubJobRepository):
        def __init__(self, job: Job):
            super().__init__(job)
            self.updated: Job | None = None

        def update(self, job: Job) -> Job:
            self.updated = job
            return super().update(job)

    job_repo = GuardJobRepo(job)
    log_repo = StubLogRepository([])

    class AsrUseCase:
        def execute(self, job_id: str) -> TranscriptionResult:
            return TranscriptionResult(
                text="audio original",
                segments=[Segment(id=0, start=0.0, end=1.0, text="audio")],
                language="pt",
                duration_sec=1.0,
                engine="openai",
            )

    class PostEditUseCase:
        def execute(self, job_id: str, transcription: TranscriptionResult) -> PostEditResult:
            return PostEditResult(text="texto divergente", segments=transcription.segments, flags=[], language="pt")

    class ArtifactUseCase:
        def execute(self, job_id: str, post_edit: PostEditResult):
            return []

    guard = TranscriptionAccuracyGuard(
        job_repository=job_repo,
        log_repository=log_repo,
        threshold=0.99,
        reference_loader=lambda _job: "referencia fiel totalmente diferente",
    )
    pipeline = ProcessJobPipeline(
        asr_use_case=AsrUseCase(),
        post_edit_use_case=PostEditUseCase(),
        artifact_use_case=ArtifactUseCase(),
        log_repository=log_repo,
        retry_handler=None,
        accuracy_guard=guard,
    )

    class MinimalController:
        def __init__(self, pipeline):
            self.pipeline_use_case = pipeline

        def process_job(self, job_id: str) -> None:
            pipeline.execute(job_id)

    controller = MinimalController(pipeline)

    app.dependency_overrides[get_job_controller_dep] = lambda: controller
    app.dependency_overrides[require_active_session] = lambda: {"user": "tester", "session_id": "sess", "csrf_token": "t"}
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    response = client.post(f"/api/jobs/{job.id}/process")
    assert response.status_code == 200, response.text
    assert job_repo.updated is not None
    assert job_repo.updated.metadata.get("accuracy_status") == "needs_review"
    assert any(entry.event == "accuracy_evaluated" and entry.level == LogLevel.WARNING for entry in log_repo.entries)

    app.dependency_overrides.clear()


def test_dashboard_summary_api_returns_counts(tmp_path, monkeypatch):
    job_pending = Job(
        id="job-summary-01",
        source_path=tmp_path / "audio1.wav",
        profile_id="profile-a",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    job_failed = Job(
        id="job-summary-02",
        source_path=tmp_path / "audio2.wav",
        profile_id="profile-b",
        engine=EngineType.OPENAI,
        status=JobStatus.FAILED,
    )
    repository = StubJobRepository([job_pending, job_failed])
    job_controller = StubJobController(repository)
    review_controller = StubReviewController()

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["summary"]["total"] == 2
    assert payload["summary"]["awaiting_review"] == 1
    assert payload["summary"]["failed"] == 1
    assert "generated_at" in payload

    app.dependency_overrides.clear()


def test_dashboard_incidents_api_returns_latest_entries(tmp_path, monkeypatch):
    entries = [
        LogEntry(job_id="job-incident-1", event="pipeline_failed", level=LogLevel.ERROR, message="ASR indisponível."),
        LogEntry(job_id="job-incident-2", event="review_flagged", level=LogLevel.WARNING, message="Aguardando revisão."),
    ]
    monkeypatch.setattr(http_app, "get_container", lambda: SimpleNamespace(log_repository=StubIncidentLogRepository(entries)))
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    response = client.get("/api/dashboard/incidents")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["items"][0]["job_id"] == "job-incident-1"
    assert payload["items"][0]["level"] == "error"
    assert payload["items"][1]["event"] == "review_flagged"
    assert "generated_at" in payload

    app.dependency_overrides.clear()


def test_api_job_logs_returns_filtered_entries(tmp_path, monkeypatch):
    job = Job(
        id="job-logs",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    entries = [
        LogEntry(job_id=job.id, event="Process started", level=LogLevel.INFO, message="ok"),
        LogEntry(job_id=job.id, event="Warning step", level=LogLevel.WARNING, message="warn"),
    ]
    app.dependency_overrides[get_job_log_service] = lambda: _make_log_service(entries)

    client = TestClient(app)
    response = client.get(
        f"/api/jobs/{job.id}/logs?page=1&page_size=1&level={LogLevel.INFO.value}"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["job_id"] == job.id
    assert payload["total"] == 1
    assert len(payload["logs"]) == 1
    assert payload["logs"][0]["event"] == "Process started"

    app.dependency_overrides.clear()


def test_api_job_logs_export_handles_formats(tmp_path, monkeypatch):
    job = Job(
        id="job-export",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    entries = [LogEntry(job_id=job.id, event="Process started", level=LogLevel.INFO, message="ok")]
    app.dependency_overrides[get_job_log_service] = lambda: _make_log_service(entries)
    client = TestClient(app)

    csv_resp = client.get(f"/api/jobs/{job.id}/logs/export?format=csv")
    assert csv_resp.status_code == 200, csv_resp.text
    assert "text/csv" in csv_resp.headers["content-type"]

    json_resp = client.get(f"/api/jobs/{job.id}/logs/export?format=json")
    assert json_resp.status_code == 200, json_resp.text
    data = json_resp.json()
    assert isinstance(data, list)
    assert data[0]["event"] == "Process started"

    app.dependency_overrides.clear()


def test_api_job_logs_requires_session(tmp_path, monkeypatch):
    job = Job(
        id="job-logs-no-session",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller

    entries = [LogEntry(job_id=job.id, event="Process started", level=LogLevel.INFO)]
    app.dependency_overrides[get_job_log_service] = lambda: _make_log_service(entries)
    # Não força sessão
    _override_app_settings(monkeypatch)
    monkeypatch.setenv("TEST_MODE", "0")
    monkeypatch.setenv("OMNI_TEST_MODE", "0")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(f"/api/jobs/{job.id}/logs")
    assert response.status_code == 401

    app.dependency_overrides.clear()


def test_api_job_logs_returns_404_for_missing_job(tmp_path, monkeypatch):
    repository = StubJobRepository([])
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_job_log_service] = lambda: _make_log_service([])
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    response = client.get("/api/jobs/missing/logs")
    assert response.status_code == 404

    app.dependency_overrides.clear()

   
def test_api_telemetry_metrics_returns_entries(tmp_path, monkeypatch):
    metrics_path = tmp_path / "metrics.log"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    entries = [
        {"timestamp": "2025-11-14T10:00:00Z", "event": "accuracy.guard.evaluated", "payload": {"job_id": "job-1"}},
        {"timestamp": "2025-11-14T10:01:00Z", "event": "artifact.download.success", "payload": {"job_id": "job-1"}},
    ]
    metrics_path.write_text("\n".join(json.dumps(entry) for entry in entries), encoding="utf-8")
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.METRICS_PATH", metrics_path)
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.ALERTS_PATH", tmp_path / "alerts.log")

    job = Job(
        id="job-telemetry",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    response = client.get("/api/telemetry/metrics")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["entries"]) == 2
    assert payload["summary"]["accuracy.guard.evaluated"]["count"] == 1

    app.dependency_overrides.clear()


def test_api_settings_page_allows_updates(tmp_path, monkeypatch):
    global app
    store = RuntimeCredentialStore(tmp_path / "runtime_credentials.json")
    monkeypatch.setattr(http_app, "_runtime_store", store)
    monkeypatch.setattr(config, "_runtime_store", store)
































































































    job = Job(
        id="job-settings",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    review_controller = StubReviewController()

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    page = client.get("/settings/api")
    assert page.status_code == 200
    assert "Whisper / ASR" in page.text

    response = client.post(
        "/settings/api",
        data={
            "target": "whisper",
            "whisper_api_key": "whisper-test-key",
            "whisper_model": "whisper-1",
            "chatgpt_api_key": "",
            "chatgpt_model": "",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert store.read()["whisper"]["api_key"] == "whisper-test-key"

    app.dependency_overrides.clear()


def test_api_settings_page_respects_feature_flag(monkeypatch):
    _force_authentication()
    _override_app_settings(monkeypatch)
    monkeypatch.setattr(http_app, "_feature_flags_snapshot", lambda: {"ui.api_settings": False})

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/settings/api")
    assert response.status_code == 404

    app.dependency_overrides.clear()


def test_api_settings_update_chatgpt_json(tmp_path, monkeypatch):
    store = RuntimeCredentialStore(tmp_path / "runtime_credentials.json")
    monkeypatch.setattr(http_app, "_runtime_store", store)
    monkeypatch.setattr(config, "_runtime_store", store)
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    response = client.post(
        "/settings/api",
        data={
            "target": "chatgpt",
            "whisper_api_key": "",
            "whisper_model": "",
            "chatgpt_api_key": "chat-test-key",
            "chatgpt_model": "gpt-4o-mini",
        },
        headers={"accept": "application/json"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["target"] == "chatgpt"
    assert store.read()["chatgpt"]["api_key"] == "chat-test-key"

    app.dependency_overrides.clear()


def test_api_settings_update_invalid_target(tmp_path, monkeypatch):
    store = RuntimeCredentialStore(tmp_path / "runtime_credentials.json")
    monkeypatch.setattr(http_app, "_runtime_store", store)
    monkeypatch.setattr(config, "_runtime_store", store)
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    response = client.post(
        "/settings/api",
        data={
            "target": "both",
            "whisper_api_key": "new-whisper",
            "whisper_model": "whisper-1",
            "chatgpt_api_key": "new-chat",
            "chatgpt_model": "gpt-4.1",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    payload = store.read()
    assert payload["whisper"]["api_key"] == "new-whisper"
    assert payload["chatgpt"]["api_key"] == "new-chat"

    app.dependency_overrides.clear()


def test_api_telemetry_metrics_returns_entries(tmp_path, monkeypatch):
    events = [
        {"timestamp": "2025-11-14T10:00:00Z", "event": "accuracy.guard.evaluated", "payload": {"job_id": "job-1"}},
        {"timestamp": "2025-11-14T10:01:00Z", "event": "artifact.download.success", "payload": {"job_id": "job-1"}},
    ]
    metrics_path = tmp_path / "metrics.log"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.METRICS_PATH", metrics_path)
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.ALERTS_PATH", tmp_path / "alerts.log")

    job = Job(
        id="job-telemetry",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    response = client.get("/api/telemetry/metrics")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert len(payload["entries"]) == 2
    assert payload["summary"]["accuracy.guard.evaluated"]["count"] == 1
    assert payload["summary"]["artifact.download.success"]["count"] == 1

    app.dependency_overrides.clear()


def test_update_job_template_returns_json_payload(tmp_path, monkeypatch):
    job = Job(
        id="job-template",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    class DummyTemplate(SimpleNamespace):
        pass

    template = DummyTemplate(id="custom", name="Custom", description="Desc")

    class DummyRegistry:
        def get(self, template_id: str):
            assert template_id == "custom"
            return template

    monkeypatch.setattr(http_app, "_template_registry", DummyRegistry(), raising=False)

    client = TestClient(app)
    response = client.post(
        f"/jobs/{job.id}/template",
        data={"template_id": "custom"},
        headers={"accept": "application/json"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["template"]["id"] == "custom"
    assert job.metadata["delivery_template"] == "custom"
    assert "delivery_template_updated_at" in job.metadata

    app.dependency_overrides.clear()


def test_update_job_locale_clears_when_empty(tmp_path, monkeypatch):
    job = Job(
        id="job-locale",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
        metadata={"delivery_locale": "pt-br"},
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    response = client.post(
        f"/jobs/{job.id}/locale",
        data={"delivery_locale": ""},
        headers={"accept": "application/json"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["locale"] is None
    assert "delivery_locale" not in job.metadata

    app.dependency_overrides.clear()


def test_artifact_download_invalid_token_returns_error(tmp_path, monkeypatch):
    job = Job(
        id="job-artifact-invalid",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    settings = _override_app_settings(monkeypatch)

    output_dir = Path(settings.base_output_dir)
    artifact_path = output_dir / job.id / "file.txt"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("conteudo", encoding="utf-8")
    job.output_paths[ArtifactType.TRANSCRIPT_TXT] = artifact_path

    params = _build_download_query(artifact_path)
    params["expires"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/artifacts",
        params={"path": str(artifact_path), "job_id": job.id, **params},
        headers={"accept": "application/json"},
        follow_redirects=False,
    )
    assert response.status_code == 401

    app.dependency_overrides.clear()


def test_job_template_update_endpoint(tmp_path, monkeypatch):
    job = Job(
        id="job-template",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    review_controller = StubReviewController()

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    response = client.post(
        f"/jobs/{job.id}/template",
        data={"template_id": "briefing"},
        headers={"Accept": "application/json"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["template"]["id"] == "briefing"
    assert "updated_at" in body
    assert job.metadata.get("delivery_template") == "briefing"

    app.dependency_overrides.clear()


def test_template_settings_page_and_creation(tmp_path, monkeypatch):
    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text(
        "---\nid: default\nname: Default\n---\n{{header}}\n\n{{transcript}}\n",
        encoding="utf-8",
    )
    original_profiles_dir = http_app._profiles_dir
    original_templates_dir = http_app._templates_dir
    monkeypatch.setattr(http_app, "_profiles_dir", templates_dir.parent)
    monkeypatch.setattr(http_app, "_templates_dir", templates_dir)
    try:
        http_app._reload_template_registry()
        _force_authentication()
        _override_app_settings(monkeypatch)

        client = TestClient(app)
        page = client.get("/settings/templates")
        assert page.status_code == 200

        response = client.post(
            "/settings/templates",
            data={
                "template_id": "cliente-x",
                "name": "Cliente X",
                "description": "Formatação específica",
                "body": "{{header}}\n\n{{transcript}}",
                "locale": "en-US",
            },
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["template"]["id"] == "cliente-x"
        assert (templates_dir / "cliente-x.template.txt").exists()

        raw = client.get("/settings/templates/cliente-x/raw")
        assert raw.status_code == 200
        assert raw.json()["locale"] == "en-us"
        preview = client.post(
            "/settings/templates/preview",
            data={"body": "{{header}}\n{{transcript}}"},
            headers={"Accept": "application/json"},
        )
        assert preview.status_code == 200
        assert "rendered" in preview.json()

        delete = client.delete("/settings/templates/cliente-x")
        assert delete.status_code == 200
        delete_missing = client.delete("/settings/templates/desconhecido")
        assert delete_missing.status_code == 404
    finally:
        app.dependency_overrides.clear()
        monkeypatch.setattr(http_app, "_profiles_dir", original_profiles_dir)
        monkeypatch.setattr(http_app, "_templates_dir", original_templates_dir)
        http_app._reload_template_registry()


def test_job_detail_renders_accuracy_and_templates(tmp_path, monkeypatch):
    job = Job(
        id="job-detail",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
        metadata={
            "delivery_template": "custom",
            "delivery_template_updated_at": "2025-11-14T12:00:00Z",
            "delivery_locale": "pt-BR",
            "accuracy_status": "passing",
            "accuracy_requires_review": "false",
            "accuracy_score": "0.98",
            "accuracy_baseline": "0.99",
            "accuracy_penalty": "0.01",
            "accuracy_wer": "0.02",
            "accuracy_updated_at": "2025-11-14T13:00:00Z",
        },
    )
    transcript = tmp_path / "output" / job.id / f"{job.id}.txt"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text("Conteúdo parcial", encoding="utf-8")
    job.output_paths[ArtifactType.TRANSCRIPT_TXT] = transcript

    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text("---\nid: default\n---\n{{transcript}}", encoding="utf-8")
    (templates_dir / "custom.template.txt").write_text("---\nid: custom\nname: Custom\n---\n{{transcript}}", encoding="utf-8")
    original_profiles = http_app._profiles_dir  # type: ignore[attr-defined]
    original_templates = http_app._templates_dir  # type: ignore[attr-defined]
    try:
        http_app._profiles_dir = templates_dir.parent  # type: ignore[attr-defined]
        http_app._templates_dir = templates_dir  # type: ignore[attr-defined]
        http_app._reload_template_registry()
        monkeypatch.setattr(
            profile_loader,
            "load_profile",
            lambda profile_id, profiles_dir: SimpleNamespace(meta={"delivery_template": "default"}),
        )

        client = TestClient(app)
        response = client.get(f"/jobs/{job.id}")
        assert response.status_code == 200, response.text
        body = response.text
        assert "Dentro da meta" in body
        assert "Custom" in body
        assert "Conteúdo parcial" in body
    finally:
        app.dependency_overrides.clear()
        http_app._profiles_dir = original_profiles  # type: ignore[attr-defined]
        http_app._templates_dir = original_templates  # type: ignore[attr-defined]
        http_app._reload_template_registry()


def test_job_detail_returns_404_when_missing(tmp_path, monkeypatch):
    repository = StubJobRepository([])
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/jobs/missing")
    assert response.status_code == 404

    app.dependency_overrides.clear()


def test_api_job_logs_export_missing_job(tmp_path, monkeypatch):
    repository = StubJobRepository([])
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_job_log_service] = lambda: _make_log_service([])
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/jobs/unknown/logs/export?format=json")
    assert response.status_code == 404

    app.dependency_overrides.clear()


def test_api_job_logs_export_invalid_format(tmp_path, monkeypatch):
    job = Job(
        id="job-logs-export",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)
    entries = [LogEntry(job_id=job.id, event="ok", level=LogLevel.INFO, message="ok")]
    app.dependency_overrides[get_job_log_service] = lambda: _make_log_service(entries)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(f"/api/jobs/{job.id}/logs/export?format=yaml")
    assert response.status_code == 400

    app.dependency_overrides.clear()


def test_job_detail_handles_profile_loader_failure(tmp_path, monkeypatch):
    job = Job(
        id="job-profile-fail",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text("---\nid: default\nname: Default\n---\n{{transcript}}", encoding="utf-8")
    original_profiles = http_app._profiles_dir  # type: ignore[attr-defined]
    original_templates = http_app._templates_dir  # type: ignore[attr-defined]
    try:
        http_app._profiles_dir = templates_dir.parent  # type: ignore[attr-defined]
        http_app._templates_dir = templates_dir  # type: ignore[attr-defined]
        http_app._reload_template_registry()

        def fail_loader(*args, **kwargs):
            raise RuntimeError("fail")

        monkeypatch.setattr(profile_loader, "load_profile", fail_loader)

        client = TestClient(app)
        response = client.get(f"/jobs/{job.id}")
        assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        http_app._profiles_dir = original_profiles  # type: ignore[attr-defined]
        http_app._templates_dir = original_templates  # type: ignore[attr-defined]
        http_app._reload_template_registry()


def test_template_crud_validations(tmp_path, monkeypatch):
    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text("---\nid: default\nname: Default\n---\n{{transcript}}", encoding="utf-8")
    original_profiles = http_app._profiles_dir  # type: ignore[attr-defined]
    original_templates = http_app._templates_dir  # type: ignore[attr-defined]
    _force_authentication()
    _override_app_settings(monkeypatch)
    try:
        http_app._profiles_dir = templates_dir.parent  # type: ignore[attr-defined]
        http_app._templates_dir = templates_dir  # type: ignore[attr-defined]
        http_app._reload_template_registry()
        client = TestClient(app)

        # create first template
        response = client.post(
            "/settings/templates",
            data={
                "template_id": "cliente-y",
                "name": "Cliente Y",
                "description": "custom",
                "body": "{{header}}",
                "locale": "en-US",
            },
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200, response.text

        # duplicate ID should fail
        duplicate = client.post(
            "/settings/templates",
            data={
                "template_id": "cliente-y",
                "body": "{{body}}",
            },
            headers={"Accept": "application/json"},
        )
        assert duplicate.status_code == 400

        # update non-existent template
        update_missing = client.post(
            "/settings/templates/missing/update",
            data={"body": "{{header}}"},
            headers={"Accept": "application/json"},
        )
        assert update_missing.status_code == 404

        # delete default template forbidden
        delete_default = client.delete("/settings/templates/default")
        assert delete_default.status_code == 400

        # raw fetch missing template
        raw_missing = client.get("/settings/templates/unknown/raw")
        assert raw_missing.status_code == 404
    finally:
        app.dependency_overrides.clear()
        http_app._profiles_dir = original_profiles  # type: ignore[attr-defined]
        http_app._templates_dir = original_templates  # type: ignore[attr-defined]
        http_app._reload_template_registry()


def test_template_creation_redirects_without_json(tmp_path, monkeypatch):
    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text("---\nid: default\nname: Default\n---\n{{transcript}}", encoding="utf-8")
    original_profiles = http_app._profiles_dir  # type: ignore[attr-defined]
    original_templates = http_app._templates_dir  # type: ignore[attr-defined]
    _force_authentication()
    _override_app_settings(monkeypatch)
    try:
        http_app._profiles_dir = templates_dir.parent  # type: ignore[attr-defined]
        http_app._templates_dir = templates_dir  # type: ignore[attr-defined]
        http_app._reload_template_registry()
        client = TestClient(app)

        response = client.post(
            "/settings/templates",
            data={
                "template_id": "cliente-redirect",
                "body": "{{header}}",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
    finally:
        app.dependency_overrides.clear()
        http_app._profiles_dir = original_profiles  # type: ignore[attr-defined]
        http_app._templates_dir = original_templates  # type: ignore[attr-defined]
        http_app._reload_template_registry()


def test_template_update_redirects_without_json(tmp_path, monkeypatch):
    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text("---\nid: default\nname: Default\n---\n{{transcript}}", encoding="utf-8")
    (templates_dir / "cliente-r.template.txt").write_text("---\nid: cliente-r\nname: Cliente R\n---\n{{transcript}}", encoding="utf-8")
    original_profiles = http_app._profiles_dir  # type: ignore[attr-defined]
    original_templates = http_app._templates_dir  # type: ignore[attr-defined]
    _force_authentication()
    _override_app_settings(monkeypatch)
    try:
        http_app._profiles_dir = templates_dir.parent  # type: ignore[attr-defined]
        http_app._templates_dir = templates_dir  # type: ignore[attr-defined]
        http_app._reload_template_registry()
        client = TestClient(app)
        response = client.post(
            "/settings/templates/cliente-r/update",
            data={"body": "{{header}}", "locale": ""},
            follow_redirects=False,
        )
        assert response.status_code == 303
    finally:
        app.dependency_overrides.clear()
        http_app._profiles_dir = original_profiles  # type: ignore[attr-defined]
        http_app._templates_dir = original_templates  # type: ignore[attr-defined]
        http_app._reload_template_registry()


def test_template_creation_requires_body(tmp_path, monkeypatch):
    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text("---\nid: default\nname: Default\n---\n{{transcript}}", encoding="utf-8")
    original_profiles = http_app._profiles_dir  # type: ignore[attr-defined]
    original_templates = http_app._templates_dir  # type: ignore[attr-defined]
    _force_authentication()
    _override_app_settings(monkeypatch)
    try:
        http_app._profiles_dir = templates_dir.parent  # type: ignore[attr-defined]
        http_app._templates_dir = templates_dir  # type: ignore[attr-defined]
        http_app._reload_template_registry()

        client = TestClient(app)
        response = client.post(
            "/settings/templates",
            data={"template_id": "cliente-z", "body": "   "},
            headers={"accept": "application/json"},
        )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()
        http_app._profiles_dir = original_profiles  # type: ignore[attr-defined]
        http_app._templates_dir = original_templates  # type: ignore[attr-defined]
        http_app._reload_template_registry()


def test_template_update_returns_json(tmp_path, monkeypatch):
    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text("---\nid: default\nname: Default\n---\n{{transcript}}", encoding="utf-8")
    (templates_dir / "cliente-q.template.txt").write_text("---\nid: cliente-q\nname: Cliente Q\n---\n{{transcript}}", encoding="utf-8")
    original_profiles = http_app._profiles_dir  # type: ignore[attr-defined]
    original_templates = http_app._templates_dir  # type: ignore[attr-defined]
    _force_authentication()
    _override_app_settings(monkeypatch)
    try:
        http_app._profiles_dir = templates_dir.parent  # type: ignore[attr-defined]
        http_app._templates_dir = templates_dir  # type: ignore[attr-defined]
        http_app._reload_template_registry()

        client = TestClient(app)
        response = client.post(
            "/settings/templates/cliente-q/update",
            data={"name": "Cliente Q+", "description": "Atualizado", "body": "{{header}}", "locale": "pt-BR"},
            headers={"accept": "application/json"},
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["template"]["name"] == "Cliente Q+"
    finally:
        app.dependency_overrides.clear()
        http_app._profiles_dir = original_profiles  # type: ignore[attr-defined]
        http_app._templates_dir = original_templates  # type: ignore[attr-defined]
        http_app._reload_template_registry()


def test_job_detail_handles_missing_template_description(tmp_path, monkeypatch):
    job = Job(
        id="job-template-missing",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
        metadata={"delivery_template": "ghost"},
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    class DummyRegistry:
        def list_templates(self):
            return []

        def get(self, template_id):
            raise FileNotFoundError("missing")

    monkeypatch.setattr(http_app, "_get_template_registry", lambda: DummyRegistry())

    client = TestClient(app)
    response = client.get(f"/jobs/{job.id}")
    assert response.status_code == 200

    app.dependency_overrides.clear()


def test_template_update_requires_body(tmp_path, monkeypatch):
    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text("---\nid: default\nname: Default\n---\n{{transcript}}", encoding="utf-8")
    (templates_dir / "cliente-empty.template.txt").write_text("---\nid: cliente-empty\nname: Cliente\n---\n{{transcript}}", encoding="utf-8")
    original_profiles = http_app._profiles_dir  # type: ignore[attr-defined]
    original_templates = http_app._templates_dir  # type: ignore[attr-defined]
    _force_authentication()
    _override_app_settings(monkeypatch)
    try:
        http_app._profiles_dir = templates_dir.parent  # type: ignore[attr-defined]
        http_app._templates_dir = templates_dir  # type: ignore[attr-defined]
        http_app._reload_template_registry()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/settings/templates/cliente-empty/update",
            data={"body": "   "},
            headers={"accept": "application/json"},
        )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.clear()
        http_app._profiles_dir = original_profiles  # type: ignore[attr-defined]
        http_app._templates_dir = original_templates  # type: ignore[attr-defined]
        http_app._reload_template_registry()


def test_template_raw_and_preview(tmp_path, monkeypatch):
    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text("---\nid: default\nname: Default\n---\n{{transcript}}", encoding="utf-8")
    original_profiles = http_app._profiles_dir  # type: ignore[attr-defined]
    original_templates = http_app._templates_dir  # type: ignore[attr-defined]
    _force_authentication()
    _override_app_settings(monkeypatch)
    try:
        http_app._profiles_dir = templates_dir.parent  # type: ignore[attr-defined]
        http_app._templates_dir = templates_dir  # type: ignore[attr-defined]
        http_app._reload_template_registry()

        client = TestClient(app)
        raw_resp = client.get("/settings/templates/default/raw")
        assert raw_resp.status_code == 200
        assert raw_resp.json()["name"] == "Default"

        preview = client.post(
            "/settings/templates/preview",
            data={"body": "{{header}}"},
            headers={"accept": "application/json"},
        )
        assert preview.status_code == 200
        assert "preview" in preview.json()["rendered"]
    finally:
        app.dependency_overrides.clear()
        http_app._profiles_dir = original_profiles  # type: ignore[attr-defined]
        http_app._templates_dir = original_templates  # type: ignore[attr-defined]
        http_app._reload_template_registry()


def test_artifact_download_returns_json_error(tmp_path, monkeypatch):
    job = Job(
        id="job-download-json",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    settings = _override_app_settings(monkeypatch, allowed_download_extensions=["txt"])
    artifact_path = Path(settings.base_output_dir) / job.id / "out.txt"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("conteudo", encoding="utf-8")
    job.output_paths[ArtifactType.TRANSCRIPT_TXT] = artifact_path

    params = _build_download_query(artifact_path)
    params["token"] = "wrong"
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/artifacts",
        params={"path": str(artifact_path), **params},
        headers={"accept": "application/json"},
    )
    assert response.status_code == 401

    app.dependency_overrides.clear()


def test_artifact_download_html_redirect(tmp_path, monkeypatch):
    job = Job(
        id="job-download-html",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app, raise_server_exceptions=False)
    params = _build_download_query(Path("output/missing.txt"))
    response = client.get(
        "/artifacts",
        params={"path": "output/missing.txt", "job_id": job.id, **params},
        headers={"accept": "text/html"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "flash=download-error" in response.headers["location"]

    app.dependency_overrides.clear()


def test_artifact_download_rate_limit_returns_429(tmp_path, monkeypatch):
    job = Job(
        id="job-download-rate",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    settings = _override_app_settings(monkeypatch, allowed_download_extensions=["txt"])
    artifact_path = Path(settings.base_output_dir) / job.id / "rate.txt"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("conteudo", encoding="utf-8")
    job.output_paths[ArtifactType.TRANSCRIPT_TXT] = artifact_path

    params = _build_download_query(artifact_path)
    client = TestClient(app, raise_server_exceptions=False)
    http_app._download_tracker.clear()
    monkeypatch.setattr(http_app, "_DOWNLOAD_RATE_LIMIT", 1, raising=False)
    monkeypatch.setattr(http_app, "_DOWNLOAD_RATE_WINDOW_SEC", 3600, raising=False)

    first = client.get("/artifacts", params={"path": str(artifact_path), **params})
    assert first.status_code == 200
    second = client.get("/artifacts", params={"path": str(artifact_path), **params})
    assert second.status_code == 429

    app.dependency_overrides.clear()


def test_update_job_template_accepts_json(tmp_path, monkeypatch):
    job = Job(
        id="job-template-update",
        source_path=tmp_path / "audio.wav",
        profile_id="teste",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text("---\nid: default\nname: Default\n---\n{{transcript}}", encoding="utf-8")
    (templates_dir / "cliente-template.template.txt").write_text("---\nid: cliente-template\nname: Cliente T\n---\n{{transcript}}", encoding="utf-8")
    original_profiles = http_app._profiles_dir  # type: ignore[attr-defined]
    original_templates = http_app._templates_dir  # type: ignore[attr-defined]
    try:
        http_app._profiles_dir = templates_dir.parent  # type: ignore[attr-defined]
        http_app._templates_dir = templates_dir  # type: ignore[attr-defined]
        http_app._reload_template_registry()

        client = TestClient(app)
        response = client.post(
            f"/jobs/{job.id}/template",
            data={"template_id": "cliente-template"},
            headers={"accept": "application/json"},
        )
        assert response.status_code == 200, response.text
        assert job.metadata["delivery_template"] == "cliente-template"
    finally:
        app.dependency_overrides.clear()
        http_app._profiles_dir = original_profiles  # type: ignore[attr-defined]
        http_app._templates_dir = original_templates  # type: ignore[attr-defined]
        http_app._reload_template_registry()


def test_update_job_template_redirect(tmp_path, monkeypatch):
    job = Job(
        id="job-template-redirect",
        source_path=tmp_path / "audio.wav",
        profile_id="teste",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "default.template.txt").write_text("---\nid: default\nname: Default\n---\n{{transcript}}", encoding="utf-8")
    original_profiles = http_app._profiles_dir  # type: ignore[attr-defined]
    original_templates = http_app._templates_dir  # type: ignore[attr-defined]
    try:
        http_app._profiles_dir = templates_dir.parent  # type: ignore[attr-defined]
        http_app._templates_dir = templates_dir  # type: ignore[attr-defined]
        http_app._reload_template_registry()

        client = TestClient(app, follow_redirects=False)
        response = client.post(f"/jobs/{job.id}/template", data={"template_id": "default"})
        assert response.status_code == 303
    finally:
        app.dependency_overrides.clear()
        http_app._profiles_dir = original_profiles  # type: ignore[attr-defined]
        http_app._templates_dir = original_templates  # type: ignore[attr-defined]
        http_app._reload_template_registry()


def test_update_job_template_missing_job(tmp_path, monkeypatch):
    repository = StubJobRepository([])
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/jobs/unknown/template", data={"template_id": "default"})
    assert response.status_code == 404

    app.dependency_overrides.clear()


def test_update_job_template_without_registry_returns_500(tmp_path, monkeypatch):
    job = Job(
        id="job-template-no-registry",
        source_path=tmp_path / "audio.wav",
        profile_id="teste",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    original_registry = http_app._get_template_registry
    monkeypatch.setattr(http_app, "_get_template_registry", lambda: None)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(f"/jobs/{job.id}/template", data={"template_id": "default"})
    assert response.status_code == 500

    app.dependency_overrides.clear()
    monkeypatch.setattr(http_app, "_get_template_registry", original_registry)


def test_update_job_locale_redirect(tmp_path, monkeypatch):
    job = Job(
        id="job-locale-redirect",
        source_path=tmp_path / "audio.wav",
        profile_id="teste",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app, follow_redirects=False)
    response = client.post(f"/jobs/{job.id}/locale", data={"delivery_locale": "pt-BR"})
    assert response.status_code == 303
    assert job.metadata["delivery_locale"] == "pt-br"

    app.dependency_overrides.clear()


def test_api_process_job_handles_exception(tmp_path, monkeypatch):
    job = Job(
        id="job-process-error-api",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)

    class FailingController(StubJobController):
        def process_job(self, job_id: str) -> None:
            raise RuntimeError("boom")

    job_controller = FailingController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(f"/api/jobs/{job.id}/process")
    assert response.status_code == 400

    app.dependency_overrides.clear()


def test_artifact_download_requires_token(tmp_path, monkeypatch):
    job = Job(
        id="job-download-missing-token",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    settings = _override_app_settings(monkeypatch, allowed_download_extensions=["txt"])
    artifact_path = Path(settings.base_output_dir) / job.id / "missingtoken.txt"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("content", encoding="utf-8")
    job.output_paths[ArtifactType.TRANSCRIPT_TXT] = artifact_path

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/artifacts",
        params={"path": str(artifact_path), "expires": "", "job_id": job.id},
        headers={"accept": "application/json"},
    )
    assert response.status_code == 401

    app.dependency_overrides.clear()


def test_artifact_download_invalid_expires(tmp_path, monkeypatch):
    job = Job(
        id="job-download-invalid-exp",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    settings = _override_app_settings(monkeypatch, allowed_download_extensions=["txt"])
    artifact_path = Path(settings.base_output_dir) / job.id / "badexp.txt"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("content", encoding="utf-8")
    job.output_paths[ArtifactType.TRANSCRIPT_TXT] = artifact_path

    params = _build_download_query(artifact_path)
    params["expires"] = "invalid-date"

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get(
        "/artifacts",
        params={"path": str(artifact_path), **params},
        headers={"accept": "application/json"},
    )
    assert response.status_code == 401

    app.dependency_overrides.clear()


def test_update_job_locale_missing_job(tmp_path, monkeypatch):
    repository = StubJobRepository([])
    job_controller = StubJobController(repository)
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/jobs/unknown/locale", data={"delivery_locale": "pt-BR"})
    assert response.status_code == 404

    app.dependency_overrides.clear()

def test_http_review_submission(tmp_path, monkeypatch):
    job = Job(
        id="job-review",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    review_controller = StubReviewController()

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    response = client.post(
        f"/jobs/{job.id}/review",
        data={"reviewer": "Ana", "decision": "approve", "notes": "ok"},
        follow_redirects=False,
    )

    assert response.status_code == 303, response.text
    assert review_controller.decisions[-1] == (job.id, True, "ok")

    app.dependency_overrides.clear()


def test_http_request_rejected_when_exceeding_limit(tmp_path, monkeypatch):
    job = Job(
        id="job-limited",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    review_controller = StubReviewController()

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    _force_authentication()
    _override_app_settings(monkeypatch, max_request_body_mb=0)

    client = TestClient(app)
    response = client.post(
        f"/jobs/{job.id}/review",
        data={"reviewer": "Ana", "decision": "approve", "notes": "ok"},
        follow_redirects=False,
    )

    assert response.status_code == 413, response.text

    app.dependency_overrides.clear()


def test_download_rejects_unsupported_extension(tmp_path, monkeypatch):
    job = Job(
        id="job-download",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    review_controller = StubReviewController()

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    _force_authentication()
    _override_app_settings(monkeypatch, allowed_download_extensions=["txt"])

    secure_file = Path("output") / job.id / "file.exe"
    secure_file.parent.mkdir(parents=True, exist_ok=True)
    secure_file.write_text("data", encoding="utf-8")

    client = TestClient(app)
    params = _build_download_query(secure_file)
    response = client.get("/artifacts", params={"path": str(secure_file), **params})

    assert response.status_code == 400, response.text

    app.dependency_overrides.clear()


def test_api_dashboard_summary_includes_accuracy(tmp_path, monkeypatch):
    job_a = Job(
        id="job-acc-a",
        source_path=tmp_path / "a.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
        metadata={"accuracy_score": "0.99", "accuracy_status": "passing", "accuracy_wer": "0.01"},
    )
    job_b = Job(
        id="job-acc-b",
        source_path=tmp_path / "b.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.ADJUSTMENTS_REQUIRED,
        metadata={"accuracy_score": "0.90", "accuracy_status": "needs_review", "accuracy_wer": "0.15"},
    )
    repository = StubJobRepository([job_a, job_b])
    job_controller = StubJobController(repository)
    review_controller = StubReviewController()

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app)
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["accuracy"]["evaluated"] == 2
    assert payload["accuracy"]["needs_review"] == 1

    app.dependency_overrides.clear()


def test_download_rate_limit_enforced(tmp_path, monkeypatch):
    job = Job(
        id="job-rate",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    review_controller = StubReviewController()
    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    _force_authentication()
    _override_app_settings(monkeypatch, allowed_download_extensions=["txt"])

    artifact_path = Path("output") / job.id / "file.txt"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text("data", encoding="utf-8")
    job.output_paths[ArtifactType.TRANSCRIPT_TXT] = artifact_path

    monkeypatch.setattr(http_app, "_DOWNLOAD_RATE_LIMIT", 1)
    monkeypatch.setattr(http_app, "_download_tracker", {})

    params = _build_download_query(artifact_path)
    client = TestClient(app)
    success = client.get("/artifacts", params={"path": str(artifact_path), **params})
    assert success.status_code == 200

    second = client.get(
        "/artifacts",
        params={"path": str(artifact_path), **params},
        headers={"accept": "application/json"},
    )
    assert second.status_code == 429

    app.dependency_overrides.clear()


def test_auth_login_generates_state(monkeypatch):
    _override_app_settings(monkeypatch)
    client = TestClient(app)
    response = client.get("/auth/login")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "url" in payload and "state" in payload
    assert payload["url"].startswith("https://auth.example.com/authorize")


def test_auth_callback_exchanges_code(monkeypatch):
    _override_app_settings(monkeypatch)

    def fake_post(url, data, timeout):
        class Resp:
            def raise_for_status(self): ...

            def json(self):
                return {"access_token": "abc", "refresh_token": "def"}

        return Resp()

    monkeypatch.setattr("src.application.services.oauth_service.requests.post", fake_post)
    client = TestClient(app)
    response = client.get("/auth/callback?code=test-code&state=my-state", headers={"accept": "application/json"})
    assert response.status_code == 200, response.text
    assert response.json()["tokens"]["access_token"] == "abc"
    assert "session_id" in response.cookies


def test_auth_login_browser_redirects(monkeypatch):
    _override_app_settings(monkeypatch)
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/auth/login/browser", follow_redirects=False)
    assert response.status_code in (302, 303)
    assert response.headers["location"].startswith("https://auth.example.com/authorize")


def test_ui_process_job_generates_flash(tmp_path, monkeypatch):
    job = Job(
        id="job-process",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    review_controller = StubReviewController()

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    _force_authentication()
    _override_app_settings(monkeypatch)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(f"/jobs/{job.id}/process", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].endswith("flash=process-started")
    assert job.id in job_controller.processed

    app.dependency_overrides.clear()


def test_theme_preview_route(monkeypatch):
    _override_app_settings(monkeypatch)
    client = TestClient(app)
    response = client.get("/ui/theme-preview")
    assert response.status_code == 200


def test_webhook_rejects_invalid_signature(monkeypatch):
    _override_app_settings(monkeypatch, webhook_secret="secret")
    client = TestClient(app)
    timestamp = str(int(time.time()))
    response = client.post(
        "/webhooks/external",
        content=b"{}",
        headers={
            "X-Signature": "invalid",
            "X-Integration-Id": "external",
            "X-Signature-Timestamp": timestamp,
        },
    )
    assert response.status_code == 401


def test_webhook_accepts_valid_signature(monkeypatch):
    settings = _override_app_settings(monkeypatch, webhook_secret="secret")
    payload = b'{"event":"ok"}'
    import hashlib, hmac

    signature = hmac.new(settings.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    client = TestClient(app)
    timestamp = str(int(time.time()))
    response = client.post(
        "/webhooks/external",
        content=payload,
        headers={
            "X-Signature": signature,
            "X-Integration-Id": "external",
            "X-Signature-Timestamp": timestamp,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "received"
    assert "trace_id" in body
    assert "latency_ms" in body


def test_routes_require_auth_without_session(tmp_path, monkeypatch):
    job = Job(
        id="job-protected",
        source_path=tmp_path / "audio.wav",
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
    )
    repository = StubJobRepository(job)
    job_controller = StubJobController(repository)
    review_controller = StubReviewController()

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    _override_app_settings(monkeypatch)
    monkeypatch.setenv("TEST_MODE", "0")
    monkeypatch.setenv("OMNI_TEST_MODE", "0")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/")
    assert response.status_code == 401

    app.dependency_overrides.clear()


def _force_authentication():
    app.dependency_overrides[require_active_session] = lambda: {
        "user": "tester",
        "session_id": "session-test",
        "csrf_token": "test-csrf",
    }


def _build_download_query(path: Path, secret: str = "secret") -> dict[str, str]:
    expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    payload = f"{path}:{expires}".encode("utf-8")
    token = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return {"token": token, "expires": expires}


def _override_app_settings(monkeypatch, **overrides):
    defaults = {
        "app_env": "test",
        "asr_engine": "openai",
        "openai_api_key": "test",
        "openai_base_url": "https://api.openai.com/v1",
        "post_edit_model": "gpt-4.1",
        "local_whisper_model_size": "medium",
        "base_input_dir": Path("inbox"),
        "base_processing_dir": Path("processing/tests"),
        "base_rejected_dir": Path("rejected"),
        "base_output_dir": Path("output"),
        "base_backup_dir": Path("backup"),
        "csv_log_path": Path("output/log.csv"),
        "max_request_body_mb": 25,
        "max_audio_size_mb": 8192,
        "openai_chunk_trigger_mb": 200,
        "openai_chunk_duration_sec": 900,
        "watcher_poll_interval": 5,
        "allowed_download_extensions": ["txt", "srt", "vtt", "json", "zip"],
        "google_sheets_enabled": False,
        "google_sheets_credentials_path": Path("config/credentials.json"),
        "google_sheets_spreadsheet_id": "",
        "google_sheets_worksheet": "Jobs",
        "s3_enabled": False,
        "s3_bucket": "transcribeflow",
        "s3_prefix": "",
        "webhook_secret": "secret",
        "webhook_signature_tolerance_sec": 300,
        "webhook_integrations_path": Path("config/test_webhook_integrations.json"),
        "oauth_client_id": "client",
        "oauth_client_secret": "secret",
        "oauth_authorize_url": "https://auth.example.com/authorize",
        "oauth_token_url": "https://auth.example.com/token",
        "oauth_redirect_uri": "https://app.example.com/callback",
        "session_ttl_minutes": 60,
    }
    defaults.update(overrides)

    class DummySettings(SimpleNamespace):
        @property
        def profiles_dir(self) -> Path:
            return Path("profiles")

        def ensure_runtime_directories(self) -> None:
            for directory in [
                Path(self.base_input_dir),
                Path(self.base_output_dir),
                Path(self.base_processing_dir),
                Path(self.base_backup_dir),
                Path(self.base_rejected_dir),
                Path(self.csv_log_path).parent,
            ]:
                Path(directory).mkdir(parents=True, exist_ok=True)

    settings = DummySettings(**defaults)
    settings.ensure_runtime_directories()
    integrations_path = Path(settings.webhook_integrations_path)
    integrations_path.parent.mkdir(parents=True, exist_ok=True)
    integrations_path.write_text(json.dumps({"external": settings.webhook_secret}), encoding="utf-8")

    monkeypatch.setattr(http_app, "get_settings", lambda: settings)
    monkeypatch.setattr(http_app, "_app_settings", settings, raising=False)
    monkeypatch.setattr("config.get_settings", lambda: settings)
    monkeypatch.setattr("infrastructure.container.service_container.get_settings", lambda: settings)
    return settings
