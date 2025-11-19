from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

from infrastructure.database.job_repository import FileJobRepository
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus


def _make_job(job_id: str, updated_at: datetime) -> Job:
    return Job(
        id=job_id,
        source_path=Path(f"inbox/{job_id}.wav"),
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.PENDING,
        created_at=updated_at,
        updated_at=updated_at,
    )


def test_file_job_repository_store_and_update(tmp_path):
    repo = FileJobRepository(tmp_path / "jobs.json")
    job = _make_job("job-1", datetime.now(timezone.utc))
    repo.create(job)

    stored = repo.find_by_id("job-1")
    assert stored and stored.id == "job-1"

    job.set_status(JobStatus.PROCESSING)
    repo.update(job)
    stored_after = repo.find_by_id("job-1")
    assert stored_after and stored_after.status == JobStatus.PROCESSING


def test_file_job_repository_list_recent_order(tmp_path):
    repo = FileJobRepository(tmp_path / "jobs.json")
    t1 = datetime(2025, 1, 1, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 2, tzinfo=timezone.utc)
    t3 = datetime(2025, 1, 3, tzinfo=timezone.utc)
    repo.create(_make_job("job-a", t1))
    repo.create(_make_job("job-b", t3))
    repo.create(_make_job("job-c", t2))

    recent = repo.list_recent(limit=2)
    assert [job.id for job in recent] == ["job-b", "job-c"]
