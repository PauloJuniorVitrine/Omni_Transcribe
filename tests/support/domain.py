from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import Segment, TranscriptionResult
from domain.entities.value_objects import JobStatus, LogLevel


class TrackingJobRepository:
    def __init__(self, job: Job) -> None:
        self.job = job
        self.updates: List[JobStatus] = []

    def find_by_id(self, job_id: str) -> Optional[Job]:
        return self.job if self.job.id == job_id else None

    def update(self, job: Job) -> Job:
        self.updates.append(job.status)
        self.job = job
        return job

    def create(self, job: Job) -> Job:  # pragma: no cover
        raise NotImplementedError

    def list_recent(self, limit: int = 50):  # pragma: no cover
        return [self.job]


class StubProfileProvider:
    def __init__(self, translate: bool) -> None:
        self.profile = Profile(
            id="juridico",
            meta={"instructions": ["translate"] if translate else []},
            prompt_body="body",
        )
        self.calls: List[str] = []

    def get(self, profile_id: str) -> Profile:
        self.calls.append(profile_id)
        return self.profile


class ControlledAsrService:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls: List[str] = []

    def run(self, job: Job, profile: Profile, task: str = "transcribe") -> TranscriptionResult:
        self.calls.append(task)
        if self.should_fail:
            raise RuntimeError("falha ASR")
        return TranscriptionResult(
            text="hello",
            segments=[Segment(id=0, start=0.0, end=1.0, text="hello")],
            language="en",
            duration_sec=12.5,
            engine=job.engine.value,
            metadata={},
        )


class LogRepositorySpy:
    def __init__(self) -> None:
        self.events: List[tuple[str, LogLevel]] = []

    def append(self, entry) -> None:  # type: ignore[override]
        self.events.append((entry.event, entry.level))

    def list_by_job(self, job_id: str):
        return [event for event in self.events if event[0] == job_id]

    def list_recent(self, limit: int = 20):
        return []


@dataclass
class StatusPublisherSpy:
    published: List[JobStatus] = field(default_factory=list)

    def publish(self, job: Job) -> None:
        self.published.append(job.status)
