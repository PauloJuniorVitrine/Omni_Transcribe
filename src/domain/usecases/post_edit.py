from __future__ import annotations

from ..entities.log_entry import LogEntry
from ..entities.transcription import PostEditResult, TranscriptionResult
from ..entities.value_objects import JobStatus, LogLevel
from ..ports.repositories import JobRepository, LogRepository, ProfileProvider
from ..ports.services import JobStatusPublisher, PostEditingService


class PostEditTranscript:
    """Runs the post-editing stage with GPT models."""

    def __init__(
        self,
        job_repository: JobRepository,
        profile_provider: ProfileProvider,
        post_edit_service: PostEditingService,
        log_repository: LogRepository,
        status_publisher: JobStatusPublisher | None = None,
    ) -> None:
        self.job_repository = job_repository
        self.profile_provider = profile_provider
        self.post_edit_service = post_edit_service
        self.log_repository = log_repository
        self.status_publisher = status_publisher

    def execute(self, job_id: str, transcription: TranscriptionResult) -> PostEditResult:
        job = self.job_repository.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} nao encontrado")

        profile = self.profile_provider.get(job.profile_id)

        job.set_status(JobStatus.POST_EDITING)
        self.job_repository.update(job)
        if self.status_publisher:
            self.status_publisher.publish(job)
        self.log_repository.append(
            LogEntry(job_id=job.id, event="post_edit_started", level=LogLevel.INFO, message="Post-edicao iniciada")
        )

        try:
            result = self.post_edit_service.run(job, profile, transcription)
            self.log_repository.append(
                LogEntry(job_id=job.id, event="post_edit_completed", level=LogLevel.INFO, message="Post-edicao concluida")
            )
            return result
        except Exception as exc:
            job.set_status(JobStatus.FAILED, notes=str(exc))
            self.job_repository.update(job)
            if self.status_publisher:
                self.status_publisher.publish(job)
            self.log_repository.append(
                LogEntry(job_id=job.id, event="post_edit_failed", level=LogLevel.ERROR, message=str(exc))
            )
            raise
