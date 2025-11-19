from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional

from domain.entities.artifact import Artifact
from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.profile import Profile
from domain.entities.transcription import PostEditResult, Segment, TranscriptionResult
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus, LogLevel


class MemoryJobRepository:
    def __init__(self) -> None:
        self.jobs: Dict[str, Job] = {}

    def create(self, job: Job) -> Job:
        self.jobs[job.id] = job
        return job

    def update(self, job: Job) -> Job:
        self.jobs[job.id] = job
        return job

    def find_by_id(self, job_id: str) -> Optional[Job]:
        return self.jobs.get(job_id)

    def list_recent(self, limit: int = 50):
        return sorted(self.jobs.values(), key=lambda j: j.updated_at, reverse=True)[:limit]


class MemoryArtifactRepository:
    def __init__(self) -> None:
        self.artifacts: List[Artifact] = []

    def save_many(self, artifacts):
        self.artifacts.extend(artifacts)

    def list_by_job(self, job_id: str):
        return [artifact for artifact in self.artifacts if artifact.job_id == job_id]


class MemoryLogRepository:
    def __init__(self) -> None:
        self.entries: List[LogEntry] = []

    def append(self, entry: LogEntry) -> None:
        self.entries.append(entry)

    def list_by_job(self, job_id: str):
        return [entry for entry in self.entries if entry.job_id == job_id]

    def list_recent(self, limit: int = 20):
        return list(reversed(self.entries))[:limit]


class MemoryReviewRepository:
    def __init__(self) -> None:
        self.reviews = []

    def save(self, review):
        self.reviews.append(review)
        return review

    def find_latest(self, job_id: str):
        return next((rev for rev in reversed(self.reviews) if rev.job_id == job_id), None)


class StubAsrService:
    def __init__(self, text: str = "stub text") -> None:
        self.text = text

    def run(self, job: Job, profile: Profile, task: str = "transcribe") -> TranscriptionResult:
        return TranscriptionResult(
            text=self.text,
            segments=[Segment(id=0, start=0.0, end=1.0, text="stub segment")],
            language="pt",
            duration_sec=1.0,
            engine=job.engine.value,
            metadata={"task": task},
        )


class StubPostEditService:
    def run(self, job: Job, profile: Profile, transcription: TranscriptionResult) -> PostEditResult:
        return PostEditResult(
            text=transcription.text.upper(),
            segments=transcription.segments,
            flags=[],
            language=transcription.language,
        )


@dataclass
class ImmediateThread:
    target: callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)

    def start(self) -> None:
        self.target(*self.args, **self.kwargs)
