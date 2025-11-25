#!/usr/bin/env python
"""
Stub FastAPI server for Playwright E2E tests.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import time
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# Ensure test mode/credentials skip are enforced in this stub environment.
os.environ.setdefault("TEST_MODE", "1")
os.environ.setdefault("OMNI_TEST_MODE", "1")
os.environ.setdefault("SKIP_RUNTIME_CREDENTIALS_VERIFY", "1")
# Desativa assinatura de download no stub para evitar 401 em previews
try:
    import config.feature_flags as ff  # type: ignore
    ff.DEFAULT_FEATURE_FLAGS["downloads.signature_required"] = False  # type: ignore[index]
except Exception:
    ...
for path in (str(ROOT), str(SRC)):
    if path not in sys.path:
        sys.path.insert(0, path)

import types
import importlib

# Provide minimal fallbacks for optional dependencies often absent in CI stubs.
try:
    import pydantic_settings  # type: ignore # noqa: F401
except ModuleNotFoundError:
    from pydantic import BaseModel

    stub_settings = types.ModuleType("pydantic_settings")

    class BaseSettings(BaseModel):  # type: ignore[misc]
        model_config: dict = {}

    def SettingsConfigDict(**kwargs):
        return kwargs

    stub_settings.BaseSettings = BaseSettings
    stub_settings.SettingsConfigDict = SettingsConfigDict
    sys.modules["pydantic_settings"] = stub_settings

try:
    import requests  # type: ignore # noqa: F401
except ModuleNotFoundError:
    requests_stub = types.ModuleType("requests")

    class RequestException(Exception):
        ...

    class Response:
        def __init__(self, status_code: int = 200, json_data: dict | None = None, text: str = "") -> None:
            self.status_code = status_code
            self._json = json_data or {}
            self.text = text

        def json(self):
            return self._json

    def _unavailable(*_args, **_kwargs):
        raise RequestException("requests stub invoked in stub_server.")

    requests_stub.Session = lambda: None  # type: ignore
    requests_stub.Response = Response
    requests_stub.RequestException = RequestException
    requests_stub.post = _unavailable  # type: ignore
    requests_stub.get = _unavailable  # type: ignore
    sys.modules["requests"] = requests_stub

try:
    import filelock  # type: ignore # noqa: F401
except ModuleNotFoundError:
    filelock_stub = types.ModuleType("filelock")

    class _FileLock:
        def __init__(self, *_args, **_kwargs) -> None:
            ...

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    filelock_stub.FileLock = _FileLock
    sys.modules["filelock"] = filelock_stub

try:
    import yaml  # type: ignore # noqa: F401
except ModuleNotFoundError:
    yaml_stub = types.ModuleType("yaml")

    def safe_load(stream):
        return {}

    def safe_dump(data, *_args, **_kwargs):
        return ""

    yaml_stub.safe_load = safe_load
    yaml_stub.safe_dump = safe_dump
    sys.modules["yaml"] = yaml_stub

# Ensure package exists
importlib.import_module("application.controllers")

job_mod = types.ModuleType("application.controllers.job_controller")
job_mod.JobController = type("JobController", (), {})
sys.modules["application.controllers.job_controller"] = job_mod

review_mod = types.ModuleType("application.controllers.review_controller")
review_mod.ReviewController = type("ReviewController", (), {})
sys.modules["application.controllers.review_controller"] = review_mod

from domain.entities.job import Job  # noqa: E402
from domain.entities.log_entry import LogEntry  # noqa: E402
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus, LogLevel  # noqa: E402
from application.services.job_log_service import JobLogService  # noqa: E402
from interfaces.http.app import app, get_job_controller_dep, get_review_controller_dep, get_job_log_service  # noqa: E402
from interfaces.http.dependencies import require_active_session  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # type: ignore  # noqa: E402


class StubJobRepository:
    def __init__(self, job: Job) -> None:
        self.jobs = [job]

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
        return job


class StubJobController:
    def __init__(self, repository: StubJobRepository) -> None:
        self.job_repository = repository
        self.processed: list[str] = []

    def list_jobs(self, limit: int = 20, page: int = 1):
        jobs = self.job_repository.list_recent(limit * page if page > 1 else limit)
        start = (page - 1) * limit
        subset = jobs[start : start + limit]
        has_more = len(jobs) > start + limit
        return subset, has_more

    def ingest_file(self, path: Path, profile_id: str, engine: EngineType) -> Job:
        job_id = f"job-{int(time.time())}"
        job = Job(
            id=job_id,
            source_path=path,
            profile_id=profile_id,
            engine=engine,
            status=JobStatus.PENDING,
        )
        self.job_repository.update(job)
        return job

    def process_job(self, job_id: str) -> None:
        self.processed.append(job_id)


class StubReviewController:
    def __init__(self, repository: StubJobRepository) -> None:
        self.repository = repository
        self.decisions: list[tuple[str, bool, str | None]] = []

    def submit_review(self, job_id: str, reviewer: str, approved: bool, notes: str | None = None) -> Job | None:
        job = self.repository.find_by_id(job_id)
        if job:
            job.set_status(JobStatus.APPROVED if approved else JobStatus.ADJUSTMENTS_REQUIRED)
        self.decisions.append((job_id, approved, notes))
        return job


def build_sample_job() -> Job:
    job_id = "job-e2e"
    audio_path = ROOT / "inbox" / f"{job_id}.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path.write_text("fake audio", encoding="utf-8")
    job = Job(
        id=job_id,
        source_path=audio_path,
        profile_id="profile-e2e",
        engine=EngineType.OPENAI,
        status=JobStatus.AWAITING_REVIEW,
        language="pt-BR",
        duration_sec=60.0,
    )
    artifact_dir = ROOT / "output" / job_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    transcript = artifact_dir / f"{job_id}_v1.txt"
    transcript.write_text("Conteudo de teste", encoding="utf-8")
    job.attach_artifact(ArtifactType.TRANSCRIPT_TXT, transcript)
    return job


def build_log_service(job: Job) -> JobLogService:
    class StubLogRepo:
        def __init__(self, entries):
            self.entries = entries

        def list_by_job(self, job_id: str):
            return [entry for entry in self.entries if entry.job_id == job_id]

    entries = [
        LogEntry(job_id=job.id, event="process_started", level=LogLevel.INFO, message="Pipeline iniciado."),
        LogEntry(job_id=job.id, event="asr_completed", level=LogLevel.INFO, message="ASR finalizado."),
    ]
    return JobLogService(StubLogRepo(entries))


def configure_overrides() -> None:
    sample_job = build_sample_job()
    repository = StubJobRepository(sample_job)
    job_controller = StubJobController(repository)
    review_controller = StubReviewController(repository)
    log_service = build_log_service(sample_job)
    app.state.e2e_job = sample_job
    app.state.e2e_repo = repository
    app.state.e2e_review = review_controller
    app.state.e2e_log_service = log_service

    app.dependency_overrides[get_job_controller_dep] = lambda: job_controller
    app.dependency_overrides[get_review_controller_dep] = lambda: review_controller
    app.dependency_overrides[get_job_log_service] = lambda: log_service
    app.dependency_overrides[require_active_session] = lambda: {"user": "e2e"}


def main() -> None:
    configure_overrides()

    @app.get("/e2e/health")
    def e2e_health():
        job = app.state.e2e_job
        return {
            "job_id": job.id,
            "status": job.status.value,
            "artifacts": [str(path) for path in job.output_paths.values()],
        }

    @app.get("/e2e/job")
    def e2e_job():
        job = app.state.e2e_job
        return {
            "id": job.id,
            "status": job.status.value,
            "engine": job.engine.value,
            "language": job.language,
        }

    @app.post("/e2e/review")
    def e2e_review(decision: str = "approve", notes: str | None = None):
        approved = decision == "approve"
        repo: StubJobRepository = app.state.e2e_repo
        review: StubReviewController = app.state.e2e_review
        job = repo.find_by_id(app.state.e2e_job.id)
        if not job:
            return JSONResponse({"detail": "job not found"}, status_code=404)
        review.submit_review(job.id, reviewer="playwright", approved=approved, notes=notes)
        return {"status": job.status.value, "decision": decision}

    @app.get("/e2e/artifact")
    def e2e_artifact():
        job = app.state.e2e_job
        if not job.output_paths:
            return JSONResponse({"detail": "no artifacts"}, status_code=404)
        first = next(iter(job.output_paths.values()))
        return FileResponse(path=first, media_type="text/plain", filename=first.name)

    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")


if __name__ == "__main__":
    main()
