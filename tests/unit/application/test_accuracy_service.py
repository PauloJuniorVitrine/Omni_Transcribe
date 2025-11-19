from __future__ import annotations

from pathlib import Path
from typing import Any

from application.services.accuracy_service import TranscriptionAccuracyGuard
from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.transcription import PostEditResult, Segment, TranscriptionResult
from domain.entities.value_objects import EngineType, JobStatus, LogLevel


class InMemoryJobRepo:
    def __init__(self) -> None:
        self.job = Job(
            id="job-accuracy",
            source_path=Path("inbox/audio.wav"),
            profile_id="geral",
            engine=EngineType.OPENAI,
            status=JobStatus.AWAITING_REVIEW,
        )

    def find_by_id(self, job_id: str) -> Job | None:
        return self.job if job_id == self.job.id else None

    def update(self, job: Job) -> Job:
        self.job = job
        return job


class InMemoryLogRepo:
    def __init__(self) -> None:
        self.entries: list[LogEntry] = []

    def append(self, entry: LogEntry) -> None:
        self.entries.append(entry)


def test_accuracy_guard_updates_metadata():
    repo = InMemoryJobRepo()
    log_repo = InMemoryLogRepo()
    guard = TranscriptionAccuracyGuard(repo, log_repo, threshold=0.95)
    transcription = TranscriptionResult(text="ola mundo", segments=[], language="pt")
    post_edit = PostEditResult(text="ola mundo", segments=[Segment(id=1, start=0, end=1, text="ola mundo", confidence=0.9)])

    guard.evaluate("job-accuracy", transcription, post_edit)

    assert repo.job.metadata["accuracy_status"] == "passing"
    assert repo.job.metadata["accuracy_requires_review"] == "false"
    assert "accuracy_score" in repo.job.metadata
    assert "accuracy_wer" in repo.job.metadata
    assert log_repo.entries[-1].level == LogLevel.INFO


def test_accuracy_guard_flags_low_quality():
    repo = InMemoryJobRepo()
    log_repo = InMemoryLogRepo()
    guard = TranscriptionAccuracyGuard(repo, log_repo, threshold=0.99)
    transcription = TranscriptionResult(text="??? ???", segments=[], language="pt")
    segments = [
        Segment(id=1, start=0, end=1, text="???", confidence=0.6),
        Segment(id=2, start=1, end=2, text="???", confidence=0.6),
    ]
    post_edit = PostEditResult(text="??? ???", segments=segments, flags=[{"type": "missing"}])

    guard.evaluate("job-accuracy", transcription, post_edit)

    assert repo.job.metadata["accuracy_status"] == "needs_review"
    assert repo.job.metadata["accuracy_requires_review"] == "true"
    assert log_repo.entries[-1].level == LogLevel.WARNING


def test_accuracy_guard_uses_reference_file_and_dispatchers(tmp_path):
    repo = InMemoryJobRepo()
    log_repo = InMemoryLogRepo()
    reference_path = tmp_path / "reference.txt"
    reference_path.write_text("ola mundo perfeito", encoding="utf-8")
    repo.job.metadata = {"reference_path": str(reference_path)}
    metrics: list[tuple[str, dict[str, Any]]] = []
    guard = TranscriptionAccuracyGuard(
        repo,
        log_repo,
        threshold=0.8,
        metric_dispatcher=lambda event, payload: metrics.append((event, payload)),
    )
    transcription = TranscriptionResult(text="ola mundo ruim", segments=[], language="pt")
    post_edit = PostEditResult(
        text="ola mundo perfeito",
        segments=[Segment(id=1, start=0, end=1, text="ola mundo perfeito", confidence=0.95)],
    )

    guard.evaluate("job-accuracy", transcription, post_edit)

    assert repo.job.metadata["accuracy_reference_source"] == "client_reference"
    assert metrics and metrics[0][0] == "accuracy.guard.evaluated"
    assert metrics[0][1]["reference_source"] == "client_reference"


def test_accuracy_guard_dispatches_alert_when_below_threshold():
    repo = InMemoryJobRepo()
    log_repo = InMemoryLogRepo()
    alerts: list[tuple[str, dict[str, Any]]] = []
    guard = TranscriptionAccuracyGuard(
        repo,
        log_repo,
        threshold=0.99,
        alert_dispatcher=lambda event, payload: alerts.append((event, payload)),
    )
    transcription = TranscriptionResult(text="???", segments=[], language="pt")
    post_edit = PostEditResult(
        text="???",
        segments=[Segment(id=1, start=0, end=1, text="???", confidence=0.4)],
        flags=[{"type": "missing"}],
    )

    guard.evaluate("job-accuracy", transcription, post_edit)

    assert alerts and alerts[0][0] == "accuracy.guard.alert"
    assert alerts[0][1]["job_id"] == "job-accuracy"
    assert repo.job.metadata["accuracy_status"] == "needs_review"


def test_accuracy_guard_returns_when_job_missing():
    repo = InMemoryJobRepo()
    log_repo = InMemoryLogRepo()
    guard = TranscriptionAccuracyGuard(repo, log_repo)
    transcription = TranscriptionResult(text="ola", segments=[], language="pt")
    post_edit = PostEditResult(text="ola", segments=[])

    guard.evaluate("invalid", transcription, post_edit)

    assert repo.job.metadata == {}
    assert log_repo.entries == []
