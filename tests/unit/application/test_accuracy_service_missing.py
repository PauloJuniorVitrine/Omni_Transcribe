from __future__ import annotations

from application.services.accuracy_service import TranscriptionAccuracyGuard
from domain.entities.job import Job
from domain.entities.transcription import PostEditResult, Segment, TranscriptionResult
from domain.entities.value_objects import LogLevel


class _Repo:
    def __init__(self, job: Job):
        self.job = job
        self.updated = False
        self.logs = []

    def find_by_id(self, job_id: str):
        return self.job if job_id == self.job.id else None

    def update(self, job):
        self.updated = True
        self.job = job
        return job

    def append(self, entry):
        self.logs.append(entry)


def test_accuracy_guard_handles_empty_segments_and_flags() -> None:
    job = Job(id="j1", source_path="a", profile_id="p")
    repo = _Repo(job)
    guard = TranscriptionAccuracyGuard(job_repository=repo, log_repository=repo, threshold=0.5)

    transcription = TranscriptionResult(text="hello world", segments=[], language="en")
    post_edit = PostEditResult(text="hello world", segments=[], flags=[])

    guard.evaluate("j1", transcription, post_edit)

    assert repo.updated is True
    assert repo.job.metadata["accuracy_requires_review"] in {"true", "false"}
    assert any(log.level in (LogLevel.INFO, LogLevel.WARNING) for log in repo.logs)
