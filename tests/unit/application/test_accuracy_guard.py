from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.transcription import PostEditResult, Segment, TranscriptionResult
from domain.entities.value_objects import JobStatus, LogLevel
from application.services.accuracy_service import TranscriptionAccuracyGuard


class StubJobRepository:
    def __init__(self, job: Job) -> None:
        self.job = job

    def find_by_id(self, job_id: str) -> Optional[Job]:
        return self.job if self.job.id == job_id else None

    def update(self, job: Job) -> Job:
        self.job = job
        return job


class StubLogRepository:
    def __init__(self) -> None:
        self.entries: List[LogEntry] = []

    def append(self, entry: LogEntry) -> None:
        self.entries.append(entry)


def make_job() -> Job:
    return Job(
        id="job-accuracy",
        source_path="inbox/sample.wav",
        profile_id="geral",
        status=JobStatus.PENDING,
    )


def make_transcription() -> TranscriptionResult:
    return TranscriptionResult(
        text="um texto de referencia",
        segments=[Segment(id=0, start=0.0, end=1.0, text="um texto", speaker=None)],
        language="pt-BR",
        duration_sec=60.0,
    )


def make_post_edit() -> PostEditResult:
    return PostEditResult(
        text="um texto editado",
        segments=[Segment(id=0, start=0.0, end=1.0, text="um texto editado", speaker=None)],
        flags=[],
        language="pt-BR",
    )


def test_accuracy_guard_marks_needs_review_with_low_score(monkeypatch):
    job = make_job()
    repo = StubJobRepository(job)
    log_repo = StubLogRepository()
    guard = TranscriptionAccuracyGuard(
        job_repository=repo,
        log_repository=log_repo,
        threshold=0.8,
        reference_loader=lambda _: "um texto externo",
    )

    transcription = make_transcription()
    post_edit = make_post_edit()
    guard.evaluate(job.id, transcription, post_edit)

    assert repo.job.metadata["accuracy_status"] == "needs_review"
    assert repo.job.metadata["accuracy_requires_review"] == "true"
    assert any(entry.event == "accuracy_evaluated" and entry.level == LogLevel.WARNING for entry in log_repo.entries)


def test_accuracy_guard_marks_passing_when_score_high():
    job = make_job()
    repo = StubJobRepository(job)
    log_repo = StubLogRepository()
    guard = TranscriptionAccuracyGuard(
        job_repository=repo,
        log_repository=log_repo,
        threshold=0.01,
    )

    transcription = make_transcription()
    post_edit = make_post_edit()
    guard.evaluate(job.id, transcription, post_edit)

    assert repo.job.metadata["accuracy_status"] == "passing"
    assert repo.job.metadata["accuracy_requires_review"] == "false"
    assert any(entry.event == "accuracy_evaluated" and entry.level == LogLevel.INFO for entry in log_repo.entries)
