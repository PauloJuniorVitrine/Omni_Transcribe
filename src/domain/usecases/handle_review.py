from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from ..entities.log_entry import LogEntry
from ..entities.user_review import UserReview
from ..entities.value_objects import JobStatus, LogLevel, ReviewDecision
from ..ports.repositories import JobRepository, LogRepository, ReviewRepository
from ..ports.services import JobStatusPublisher


@dataclass
class ReviewInput:
    job_id: str
    reviewer: str
    approved: bool
    notes: Optional[str] = None


class HandleReviewDecision:
    """Persist review decisions and update job status."""

    def __init__(
        self,
        job_repository: JobRepository,
        review_repository: ReviewRepository,
        log_repository: LogRepository,
        status_publisher: JobStatusPublisher | None = None,
    ) -> None:
        self.job_repository = job_repository
        self.review_repository = review_repository
        self.log_repository = log_repository
        self.status_publisher = status_publisher

    def execute(self, data: ReviewInput) -> UserReview:
        job = self.job_repository.find_by_id(data.job_id)
        if not job:
            raise ValueError(f"Job {data.job_id} nao encontrado")

        decision = ReviewDecision.APPROVED if data.approved else ReviewDecision.NEEDS_ADJUSTMENT
        job.set_status(JobStatus.APPROVED if data.approved else JobStatus.ADJUSTMENTS_REQUIRED, notes=data.notes)
        self.job_repository.update(job)
        if self.status_publisher:
            self.status_publisher.publish(job)

        review = UserReview(
            id=uuid4().hex, job_id=job.id, reviewer=data.reviewer, decision=decision, notes=data.notes
        )
        self.review_repository.save(review)

        self.log_repository.append(
            LogEntry(
                job_id=job.id,
                event="review_completed",
                level=LogLevel.INFO,
                message=f"Decisao: {decision.value}",
            )
        )
        return review
