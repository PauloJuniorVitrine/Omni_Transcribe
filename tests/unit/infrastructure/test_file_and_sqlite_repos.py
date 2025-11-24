from __future__ import annotations

from pathlib import Path

from domain.entities.job import Job
from domain.entities.user_review import UserReview
from domain.entities.value_objects import ReviewDecision
from infrastructure.database import file_storage
from infrastructure.database.job_repository import FileJobRepository
from infrastructure.database.review_repository import FileReviewRepository
from infrastructure.database.sqlite_repositories import SqlJobRepository


def test_file_storage_reads_empty_when_missing(tmp_path: Path) -> None:
    data = file_storage.read_json_list(tmp_path / "missing.json")
    assert data == []


def test_file_job_repository_update_appends_when_missing(tmp_path: Path) -> None:
    repo = FileJobRepository(tmp_path / "jobs.json")
    job = Job(id="j", source_path=tmp_path / "a.wav", profile_id="p")
    repo.update(job)
    assert repo.find_by_id("j") is not None


def test_review_repository_find_latest_none(tmp_path: Path) -> None:
    repo = FileReviewRepository(tmp_path / "reviews.json")
    assert repo.find_latest("missing") is None


def test_sql_job_repository_list_recent(tmp_path: Path) -> None:
    repo = SqlJobRepository(tmp_path / "db.sqlite")
    job = Job(id="j", source_path=tmp_path / "a.wav", profile_id="p")
    repo.create(job)
    jobs = repo.list_recent()
    assert jobs and jobs[0].id == "j"
