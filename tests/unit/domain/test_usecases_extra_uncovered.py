from __future__ import annotations

import pytest

from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import TranscriptionResult
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus, LogLevel, ReviewDecision
from domain.usecases.generate_artifacts import GenerateArtifacts
from domain.usecases.handle_review import HandleReviewDecision, ReviewInput
from domain.usecases.register_delivery import RegisterDelivery
from domain.usecases.retry_or_reject import RetryDecision, RetryOrRejectJob
from domain.usecases.run_asr import RunAsrPipeline


class _Repo:
    def __init__(self, job: Job):
        self.job = job
        self.saved_artifacts = []
        self.logs = []

    def find_by_id(self, job_id: str):
        return self.job if job_id == self.job.id else None

    def update(self, job):
        self.job = job
        return job

    def append(self, entry):
        self.logs.append(entry)

    def save_many(self, artifacts):
        self.saved_artifacts.extend(list(artifacts))

    def list_by_job(self, job_id: str):
        return []

    def save(self, review):
        self.review = review
        return review

    def list_recent(self, limit=20):
        return []


def test_run_asr_raises_when_job_missing() -> None:
    repo = _Repo(Job(id="x", source_path="a", profile_id="p"))
    uc = RunAsrPipeline(job_repository=repo, profile_provider=lambda pid: Profile(id=pid, meta={}, prompt_body=""), asr_service=None, log_repository=repo)
    with pytest.raises(ValueError):
        uc.execute("missing")


def test_retry_or_reject_marks_rejected() -> None:
    job = Job(id="j", source_path="a", profile_id="p")
    repo = _Repo(job)
    uc = RetryOrRejectJob(job_repository=repo, log_repository=repo)
    decision = RetryDecision(job_id="j", error_message="err", retryable=False, stage="pipeline", payload={"x": 1})
    updated = uc.execute(decision)
    assert updated.status == JobStatus.REJECTED
    assert repo.logs[-1].level == LogLevel.WARNING


def test_generate_artifacts_raises_when_job_missing() -> None:
    repo = _Repo(Job(id="j", source_path="a", profile_id="p"))

    class _Builder:
        def build(self, job, profile, post_edit_result):
            return []

    uc = GenerateArtifacts(
        job_repository=repo,
        artifact_repository=repo,
        artifact_builder=_Builder(),
        log_repository=repo,
        profile_provider=lambda pid: Profile(id=pid, meta={}, prompt_body=""),
    )
    with pytest.raises(ValueError):
        uc.execute("missing", None)  # type: ignore[arg-type]


def test_register_delivery_requires_approved_job() -> None:
    job = Job(id="j", source_path="a", profile_id="p", status=JobStatus.AWAITING_REVIEW)
    repo = _Repo(job)

    class _Package:
        def create_package(self, job, artifacts):
            return "pkg"

    uc = RegisterDelivery(
        job_repository=repo,
        artifact_repository=repo,
        package_service=_Package(),
        delivery_logger=lambda job, package_path: None,
        log_repository=repo,
    )
    with pytest.raises(ValueError):
        uc.execute("j")


def test_handle_review_missing_job_raises() -> None:
    job = Job(id="j", source_path="a", profile_id="p")
    repo = _Repo(job)
    uc = HandleReviewDecision(
        job_repository=repo,
        review_repository=repo,
        log_repository=repo,
    )
    with pytest.raises(ValueError):
        uc.execute(ReviewInput(job_id="missing", reviewer="r", approved=True))
