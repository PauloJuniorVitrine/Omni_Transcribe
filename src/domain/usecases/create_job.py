from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional
from uuid import uuid4
from datetime import datetime, timezone

from ..entities.job import Job
from ..entities.value_objects import EngineType, JobStatus
from ..ports.repositories import JobRepository, LogRepository, ProfileProvider
from ..entities.log_entry import LogEntry
from ..entities.value_objects import LogLevel
from ..ports.services import JobStatusPublisher


@dataclass
class CreateJobInput:
    source_path: Path
    profile_id: Optional[str] = None
    engine: EngineType = EngineType.OPENAI
    metadata: Dict[str, str] = field(default_factory=dict)


class CreateJobFromInbox:
    """Create a Job when a new audio file is discovered in inbox/."""

    def __init__(
        self,
        job_repository: JobRepository,
        profile_provider: ProfileProvider,
        log_repository: LogRepository,
        default_profile: str = "geral",
        status_publisher: JobStatusPublisher | None = None,
    ) -> None:
        self.job_repository = job_repository
        self.profile_provider = profile_provider
        self.log_repository = log_repository
        self.default_profile = default_profile
        self.status_publisher = status_publisher

    def execute(self, data: CreateJobInput) -> Job:
        profile_id = data.profile_id or self.default_profile
        # Validate profile existence through provider (raises if missing).
        profile = self.profile_provider.get(profile_id)

        job_id = uuid4().hex
        metadata = {**data.metadata, "source_folder": data.source_path.parent.name}
        profile_meta = profile.meta or {}
        template_id = profile_meta.get("delivery_template")
        if template_id and "delivery_template" not in metadata:
            metadata["delivery_template"] = str(template_id)
            metadata["delivery_template_updated_at"] = datetime.now(timezone.utc).isoformat()
        preferred_locale = data.metadata.get("delivery_locale") or profile_meta.get("default_locale") or profile_meta.get("language")
        normalized_locale = _normalize_locale_code(preferred_locale)
        if normalized_locale:
            metadata["delivery_locale"] = normalized_locale
            metadata["delivery_locale_updated_at"] = datetime.now(timezone.utc).isoformat()
        job = Job(
            id=job_id,
            source_path=data.source_path,
            profile_id=profile_id,
            status=JobStatus.PENDING,
            engine=data.engine,
            metadata=metadata,
        )
        self.job_repository.create(job)
        self.log_repository.append(
            LogEntry(
                job_id=job.id,
                event="job_created",
                level=LogLevel.INFO,
                message=f"Job criado a partir do arquivo {data.source_path}",
            )
        )
        if self.status_publisher:
            self.status_publisher.publish(job)
        return job


def _normalize_locale_code(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    slug = value.strip().replace("_", "-").lower()
    if len(slug) < 2:
        return None
    return slug
