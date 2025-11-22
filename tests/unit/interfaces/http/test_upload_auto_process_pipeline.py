from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from fastapi.testclient import TestClient

from interfaces.http.app import app, get_job_controller_dep
from interfaces.http.dependencies import require_active_session
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus, ArtifactType


class _MemoryJobRepo:
    def __init__(self) -> None:
        self.jobs: Dict[str, Job] = {}

    def create(self, job: Job) -> Job:
        self.jobs[job.id] = job
        return job

    def update(self, job: Job) -> Job:
        self.jobs[job.id] = job
        return job

    def find_by_id(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    def list_recent(self, limit: int = 50) -> List[Job]:
        return list(self.jobs.values())[:limit]


class _StubCreateJob:
    def __init__(self, repo: _MemoryJobRepo) -> None:
        self.repo = repo

    def execute(self, data):
        job = Job(
            id="job-auto",
            source_path=Path(data.source_path),
            profile_id=data.profile_id or "geral",
            engine=data.engine,
            metadata=data.metadata,
        )
        self.repo.create(job)
        return job


class _StubPipeline:
    def __init__(self, repo: _MemoryJobRepo) -> None:
        self.repo = repo
        self.executed: List[str] = []

    def execute(self, job_id: str):
        job = self.repo.find_by_id(job_id)
        if not job:
            raise ValueError("job not found")
        job.metadata["accuracy_score"] = "0.95"
        job.metadata["accuracy_status"] = "passing"
        job.output_paths = {ArtifactType.TRANSCRIPT_TXT: Path("output.txt")}
        job.set_status(JobStatus.AWAITING_REVIEW)
        self.repo.update(job)
        self.executed.append(job_id)


class _StubJobController:
    def __init__(self) -> None:
        self.repo = _MemoryJobRepo()
        self.create_job_use_case = _StubCreateJob(self.repo)
        self.pipeline_use_case = _StubPipeline(self.repo)
        self.retry_use_case = None

    @property
    def job_repository(self):
        return self.repo

    def ingest_file(self, path, profile_id, engine):
        return self.create_job_use_case.execute(
            type("Input", (), {"source_path": path, "profile_id": profile_id, "engine": engine, "metadata": {}})()
        )

    def process_job(self, job_id: str) -> None:
        self.pipeline_use_case.execute(job_id)


def test_upload_auto_process_sets_accuracy_metadata(tmp_path):
    controller = _StubJobController()
    app.dependency_overrides[get_job_controller_dep] = lambda: controller
    app.dependency_overrides[require_active_session] = lambda: {}
    client = TestClient(app)

    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"RIFF0000")
    files = {"file": ("audio.wav", audio.read_bytes(), "audio/wav")}
    data = {"profile": "geral", "engine": EngineType.OPENAI.value, "auto_process": "true"}

    resp = client.post("/jobs/upload", files=files, data=data, headers={"accept": "application/json"})
    assert resp.status_code in (200, 303, 307)

    job = controller.repo.list_recent(1)[0]
    assert job.metadata.get("accuracy_score") == "0.95"
    assert job.status == JobStatus.AWAITING_REVIEW
    assert controller.pipeline_use_case.executed == [job.id]

    app.dependency_overrides.clear()
