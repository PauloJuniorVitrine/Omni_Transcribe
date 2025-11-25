from __future__ import annotations

from pathlib import Path

from domain.entities.artifact import Artifact
from domain.entities.job import Job
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus
from domain.entities.log_entry import LogEntry, LogLevel
from infrastructure.database.artifact_repository import FileArtifactRepository
from infrastructure.database.log_repository import FileLogRepository


def make_job() -> Job:
    return Job(
        id="job-repo",
        source_path=Path("inbox/sample.wav"),
        profile_id="geral",
        status=JobStatus.PENDING,
        engine=EngineType.OPENAI,
    )


def make_artifact(job: Job, artifact_type: ArtifactType) -> Artifact:
    return Artifact(
        id=f"{artifact_type.value}-id",
        job_id=job.id,
        artifact_type=artifact_type,
        path=Path(f"output/{job.id}/{artifact_type.value}.txt"),
    )


def test_file_artifact_repository_persists(tmp_path):
    job = make_job()
    repo = FileArtifactRepository(tmp_path / "artifacts.json")
    artifacts = [make_artifact(job, ArtifactType.TRANSCRIPT_TXT), make_artifact(job, ArtifactType.SUBTITLE_SRT)]
    repo.save_many(artifacts)

    stored = repo.list_by_job(job.id)
    assert len(stored) == 2
    assert {item.artifact_type for item in stored} == {ArtifactType.TRANSCRIPT_TXT, ArtifactType.SUBTITLE_SRT}


def test_file_log_repository_appends_and_reads(tmp_path):
    job = make_job()
    repo = FileLogRepository(tmp_path / "logs.json")
    entry = LogEntry(job_id=job.id, event="test", level=LogLevel.INFO, message="ok")
    repo.append(entry)

    recovered = repo.list_by_job(job.id)
    assert len(recovered) == 1
    assert recovered[0].event == "test"
