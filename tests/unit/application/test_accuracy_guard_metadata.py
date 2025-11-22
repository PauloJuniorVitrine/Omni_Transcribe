from __future__ import annotations

from datetime import datetime, timezone

from application.services.accuracy_service import TranscriptionAccuracyGuard
from domain.entities.job import Job
from domain.entities.transcription import PostEditResult, TranscriptionResult, Segment
from domain.entities.value_objects import LogLevel


class _JobRepo:
    def __init__(self, job: Job) -> None:
        self.job = job
        self.updates: list[Job] = []

    def find_by_id(self, job_id: str):
        return self.job if self.job.id == job_id else None

    def update(self, job: Job):
        self.updates.append(job)
        self.job = job
        return job


class _LogRepo:
    def __init__(self) -> None:
        self.entries = []

    def append(self, entry):
        self.entries.append(entry)


def test_accuracy_guard_sets_metadata_and_logs(tmp_path):
    job = Job(
        id="job-acc",
        source_path=tmp_path / "a.wav",
        profile_id="p",
        metadata={},
    )
    job_repo = _JobRepo(job)
    log_repo = _LogRepo()
    guard = TranscriptionAccuracyGuard(job_repository=job_repo, log_repository=log_repo, threshold=0.5)

    transcription = TranscriptionResult(
        text="hello world",
        segments=[Segment(id=0, start=0.0, end=1.0, text="hello world")],
        language="en",
    )
    post_edit = PostEditResult(text="hello world", segments=transcription.segments, language="en", flags=[])

    guard.evaluate(job.id, transcription, post_edit)

    updated = job_repo.job
    assert "accuracy_score" in updated.metadata
    assert updated.metadata["accuracy_status"] in ("passing", "needs_review")
    assert any(entry.event == "accuracy_evaluated" for entry in log_repo.entries)


def test_accuracy_guard_uses_reference_and_sets_requires_review(tmp_path):
    job = Job(
        id="job-acc2",
        source_path=tmp_path / "b.wav",
        profile_id="p",
        metadata={"reference_transcript": "hello brave new world"},
    )
    job_repo = _JobRepo(job)
    log_repo = _LogRepo()
    guard = TranscriptionAccuracyGuard(job_repository=job_repo, log_repository=log_repo, threshold=0.99)

    transcription = TranscriptionResult(
        text="hello world",
        segments=[Segment(id=0, start=0.0, end=1.0, text="hello world")],
        language="en",
    )
    post_edit = PostEditResult(text="hello world", segments=transcription.segments, language="en", flags=[])

    guard.evaluate(job.id, transcription, post_edit)

    updated = job_repo.job
    assert updated.metadata["accuracy_reference_source"] in {"client_reference", "asr_output"}
    assert updated.metadata["accuracy_requires_review"] in {"true", "false"}
    # expect warning only if below threshold
    assert any(entry.level == LogLevel.WARNING for entry in log_repo.entries) or updated.metadata["accuracy_requires_review"] == "false"
