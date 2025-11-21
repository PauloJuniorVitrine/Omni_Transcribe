from __future__ import annotations

from typing import Optional

from domain.entities.job import Job
from domain.usecases.handle_review import HandleReviewDecision, ReviewInput
from domain.usecases.register_delivery import RegisterDelivery
from domain.ports.repositories import JobRepository

from application.services.sheet_service import CsvSheetService


class ReviewController:
    """Coordinates review decisions and bookkeeping."""

    def __init__(
        self,
        job_repository: JobRepository,
        handle_review_use_case: HandleReviewDecision,
        sheet_service: CsvSheetService,
        register_delivery_use_case: Optional[RegisterDelivery] = None,
    ) -> None:
        self.job_repository = job_repository
        self.handle_review_use_case = handle_review_use_case
        self.sheet_service = sheet_service
        self.register_delivery_use_case = register_delivery_use_case

    def submit_review(self, job_id: str, reviewer: str, approved: bool, notes: Optional[str] = None) -> Job:
        payload = ReviewInput(job_id=job_id, reviewer=reviewer, approved=approved, notes=notes)
        self.handle_review_use_case.execute(payload)
        job = self.job_repository.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} nao encontrado apos a revisao.")
        if approved and self.register_delivery_use_case:
            self.register_delivery_use_case.execute(job_id)
        return job
