from __future__ import annotations

from typing import Iterable, List, Optional, Protocol

from ..entities.artifact import Artifact
from ..entities.job import Job
from ..entities.log_entry import LogEntry
from ..entities.profile import Profile
from ..entities.user_review import UserReview


class JobRepository(Protocol):
    def create(self, job: Job) -> Job: ...

    def update(self, job: Job) -> Job: ...

    def find_by_id(self, job_id: str) -> Optional[Job]: ...

    def list_recent(self, limit: int = 50) -> List[Job]: ...


class ArtifactRepository(Protocol):
    def save_many(self, artifacts: Iterable[Artifact]) -> None: ...

    def list_by_job(self, job_id: str) -> List[Artifact]: ...


class LogRepository(Protocol):
    def append(self, entry: LogEntry) -> None: ...

    def list_by_job(self, job_id: str) -> List[LogEntry]: ...

    def list_recent(self, limit: int = 20) -> List[LogEntry]: ...


class ReviewRepository(Protocol):
    def save(self, review: UserReview) -> UserReview: ...

    def find_latest(self, job_id: str) -> Optional[UserReview]: ...


class ProfileProvider(Protocol):
    def get(self, profile_id: str) -> Profile: ...
