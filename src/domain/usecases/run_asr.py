from __future__ import annotations

from ..entities.log_entry import LogEntry
from ..entities.transcription import TranscriptionResult
from ..entities.value_objects import JobStatus, LogLevel
from ..ports.repositories import JobRepository, LogRepository, ProfileProvider
from ..ports.services import AsrService, JobStatusPublisher


class RunAsrPipeline:
    """Executes the ASR step for a job using the configured engine."""

    def __init__(
        self,
        job_repository: JobRepository,
        profile_provider: ProfileProvider,
        asr_service: AsrService,
        log_repository: LogRepository,
        status_publisher: JobStatusPublisher | None = None,
    ) -> None:
        self.job_repository = job_repository
        self.profile_provider = profile_provider
        self.asr_service = asr_service
        self.log_repository = log_repository
        self.status_publisher = status_publisher

    def execute(self, job_id: str) -> TranscriptionResult:
        job = self.job_repository.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} nao encontrado")

        profile = self.profile_provider.get(job.profile_id)
        task = "translate" if profile.requires_translation() else "transcribe"

        job.set_status(JobStatus.PROCESSING)
        self.job_repository.update(job)
        if self.status_publisher:
            self.status_publisher.publish(job)
        self.log_repository.append(
            LogEntry(job_id=job.id, event="asr_started", level=LogLevel.INFO, message=f"Tarefa: {task}")
        )

        try:
            result = self.asr_service.run(job, profile, task=task)
            job.language = result.language
            job.duration_sec = result.duration_sec
            job.set_status(JobStatus.ASR_COMPLETED)
            self.job_repository.update(job)
            if self.status_publisher:
                self.status_publisher.publish(job)
            self.log_repository.append(
                LogEntry(job_id=job.id, event="asr_completed", level=LogLevel.INFO, message=f"Idioma: {result.language}")
            )
            return result
        except Exception as exc:
            job.set_status(JobStatus.FAILED, notes=str(exc))
            self.job_repository.update(job)
            if self.status_publisher:
                self.status_publisher.publish(job)
            self.log_repository.append(
                LogEntry(job_id=job.id, event="asr_failed", level=LogLevel.ERROR, message=str(exc))
            )
            raise
