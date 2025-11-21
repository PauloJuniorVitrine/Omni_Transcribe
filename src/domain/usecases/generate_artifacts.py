from __future__ import annotations

from typing import Iterable, List

from ..entities.artifact import Artifact
from ..entities.log_entry import LogEntry
from ..entities.transcription import PostEditResult
from ..entities.value_objects import JobStatus, LogLevel
from ..ports.repositories import ArtifactRepository, JobRepository, LogRepository, ProfileProvider
from ..ports.services import ArtifactBuilder, JobStatusPublisher


class GenerateArtifacts:
    """Generate TXT/SRT/VTT/JSON artifacts after post-editing."""

    def __init__(
        self,
        job_repository: JobRepository,
        artifact_repository: ArtifactRepository,
        artifact_builder: ArtifactBuilder,
        log_repository: LogRepository,
        profile_provider: ProfileProvider,
        status_publisher: JobStatusPublisher | None = None,
    ) -> None:
        self.job_repository = job_repository
        self.artifact_repository = artifact_repository
        self.artifact_builder = artifact_builder
        self.log_repository = log_repository
        self.profile_provider = profile_provider
        self.status_publisher = status_publisher

    def execute(self, job_id: str, post_edit_result: PostEditResult) -> List[Artifact]:
        job = self.job_repository.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} nao encontrado")

        profile = self.profile_provider.get(job.profile_id)
        artifacts: Iterable[Artifact] = self.artifact_builder.build(job, profile, post_edit_result)
        materialized = list(artifacts)
        self.artifact_repository.save_many(materialized)

        for artifact in materialized:
            job.attach_artifact(artifact.artifact_type, artifact.path)

        job.set_status(JobStatus.AWAITING_REVIEW)
        self.job_repository.update(job)
        if self.status_publisher:
            self.status_publisher.publish(job)

        self.log_repository.append(
            LogEntry(
                job_id=job.id,
                event="artifacts_generated",
                level=LogLevel.INFO,
                message=f"{len(materialized)} artefatos criados",
            )
        )
        return materialized
