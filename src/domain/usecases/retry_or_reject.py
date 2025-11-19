from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from ..entities.job import Job
from ..entities.log_entry import LogEntry
from ..entities.value_objects import JobStatus, LogLevel
from ..ports.repositories import JobRepository, LogRepository
from ..ports.services import JobStatusPublisher, RejectedJobLogger


@dataclass
class RetryDecision:
    job_id: str
    error_message: str
    retryable: bool = True
    stage: str = "pipeline"
    payload: Dict[str, object] = field(default_factory=dict)


class RetryOrRejectJob:
    """Decide se um job volta para a fila ou vai para rejected/."""

    def __init__(
        self,
        job_repository: JobRepository,
        log_repository: LogRepository,
        rejected_logger: Optional[RejectedJobLogger] = None,
        status_publisher: Optional[JobStatusPublisher] = None,
    ) -> None:
        self.job_repository = job_repository
        self.log_repository = log_repository
        self.rejected_logger = rejected_logger
        self.status_publisher = status_publisher

    def execute(self, decision: RetryDecision) -> Job:
        job = self.job_repository.find_by_id(decision.job_id)
        if not job:
            raise ValueError(f"Job {decision.job_id} não encontrado")

        if decision.retryable:
            job.bump_version()
            job.set_status(JobStatus.PENDING, notes=decision.error_message)
            event = "job_requeued"
        else:
            job.set_status(JobStatus.REJECTED, notes=decision.error_message)
            event = "job_rejected"
            if self.rejected_logger:
                self.rejected_logger.record(job, decision.error_message, decision.stage, decision.payload)

        self.job_repository.update(job)
        if self.status_publisher:
            self.status_publisher.publish(job)
        self.log_repository.append(
            LogEntry(job_id=job.id, event=event, level=LogLevel.WARNING, message=decision.error_message)
        )
        return job
