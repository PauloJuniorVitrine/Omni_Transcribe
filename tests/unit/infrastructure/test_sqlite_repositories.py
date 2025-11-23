from __future__ import annotations

import json
from pathlib import Path

from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.user_review import UserReview
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus, LogLevel, ReviewDecision
from domain.entities.artifact import Artifact
from infrastructure.database.sqlite_repositories import (
    SqlArtifactRepository,
    SqlJobRepository,
    SqlLogRepository,
    SqlReviewRepository,
)


def _make_job(job_id: str) -> Job:
    return Job(
        id=job_id,
        source_path=Path(f"inbox/{job_id}.wav"),
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.PENDING,
    )


def test_sqlite_repositories_crud(tmp_path: Path):
    db_path = tmp_path / "tf.db"
    job_repo = SqlJobRepository(db_path)
    log_repo = SqlLogRepository(db_path)
    art_repo = SqlArtifactRepository(db_path)
    review_repo = SqlReviewRepository(db_path)

    job = _make_job("job-1")
    job_repo.create(job)
    assert job_repo.find_by_id("job-1").id == "job-1"

    log_repo.append(LogEntry(job_id="job-1", event="created", level=LogLevel.INFO, message="ok"))
    logs = log_repo.list_by_job("job-1")
    assert len(logs) == 1

    artifact = Artifact(id="art-1", job_id="job-1", artifact_type=ArtifactType.TRANSCRIPT_TXT, path=Path("out.txt"), version=1)
    art_repo.save_many([artifact])
    assert art_repo.list_by_job("job-1")[0].id == "art-1"

    review = UserReview(id="rev-1", job_id="job-1", reviewer="alice", decision=ReviewDecision.APPROVED, notes=None)
    review_repo.save(review)
    stored_review = review_repo.find_latest("job-1")
    assert stored_review and stored_review.reviewer == "alice"

    # recent list uses updated_at ordering; ensure JSON payload preserved
    recent = job_repo.list_recent(10)
    assert recent and recent[0].id == "job-1"
    assert isinstance(json.loads(job_repo.conn.execute("SELECT payload FROM jobs").fetchone()[0]), dict)
