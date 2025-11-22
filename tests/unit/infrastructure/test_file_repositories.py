from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone, timedelta

from domain.entities.artifact import Artifact
from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.user_review import UserReview
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus, LogLevel, ReviewDecision
from infrastructure.database.artifact_repository import FileArtifactRepository
from infrastructure.database.log_repository import FileLogRepository
from infrastructure.database.review_repository import FileReviewRepository


def _job(tmp_path: Path) -> Job:
    return Job(
        id="j1",
        source_path=tmp_path / "audio.wav",
        profile_id="p",
        engine=EngineType.OPENAI,
        status=JobStatus.PENDING,
    )


def test_file_artifact_repository_save_and_list(tmp_path):
    repo = FileArtifactRepository(tmp_path / "artifacts.json")
    art = Artifact(id="a1", job_id="j1", artifact_type=ArtifactType.TRANSCRIPT_TXT, path=tmp_path / "f.txt", version=1)

    repo.save_many([art])
    stored = repo.list_by_job("j1")

    assert len(stored) == 1
    assert stored[0].artifact_type == ArtifactType.TRANSCRIPT_TXT


def test_file_log_repository_appends_and_orders(tmp_path):
    repo = FileLogRepository(tmp_path / "logs.json")
    older = LogEntry(job_id="j1", event="older", level=LogLevel.INFO, message=None, timestamp=datetime.now(timezone.utc) - timedelta(seconds=10))
    newer = LogEntry(job_id="j1", event="newer", level=LogLevel.INFO)
    repo.append(older)
    repo.append(newer)

    entries = repo.list_by_job("j1")
    assert [e.event for e in entries] == ["older", "newer"]
    recent = repo.list_recent(limit=1)[0]
    assert recent.event == "newer"


def test_file_review_repository_latest(tmp_path):
    repo = FileReviewRepository(tmp_path / "reviews.json")
    older = UserReview(id="r1", job_id="j1", reviewer="ana", decision=ReviewDecision.APPROVED, timestamp=datetime.now(timezone.utc) - timedelta(seconds=5))
    newer = UserReview(id="r2", job_id="j1", reviewer="bob", decision=ReviewDecision.NEEDS_ADJUSTMENT)
    repo.save(older)
    repo.save(newer)

    latest = repo.find_latest("j1")
    assert latest
    assert latest.id == "r2"
