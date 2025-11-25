from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from domain.entities.job import Job
from domain.entities.value_objects import EngineType
from domain.usecases.create_job import CreateJobFromInbox, CreateJobInput
from domain.usecases.pipeline import ProcessJobPipeline
from domain.usecases.retry_or_reject import RetryDecision, RetryOrRejectJob
from domain.ports.repositories import JobRepository


class JobController:
    """Application-level orchestration for job lifecycle exposed via interfaces."""

    def __init__(
        self,
        job_repository: JobRepository,
        create_job_use_case: CreateJobFromInbox,
        pipeline_use_case: Optional[ProcessJobPipeline],
        retry_use_case: RetryOrRejectJob,
    ) -> None:
        self.job_repository = job_repository
        self.create_job_use_case = create_job_use_case
        self.pipeline_use_case = pipeline_use_case
        self.retry_use_case = retry_use_case

    def list_jobs(self, limit: int = 20, page: int = 1) -> tuple[List[Job], bool]:
        page = max(page, 1)
        limit = max(limit, 1)
        window = (limit * page) + 1  # fetch a bit extra to detect next page
        jobs = self.job_repository.list_recent(window)
        start = (page - 1) * limit
        page_items = jobs[start : start + limit]
        has_more = len(jobs) > start + limit
        return page_items, has_more

    def ingest_file(self, path: Path, profile_id: str, engine: EngineType) -> Job:
        input_data = CreateJobInput(source_path=path, profile_id=profile_id, engine=engine)
        return self.create_job_use_case.execute(input_data)

    def process_job(self, job_id: str) -> None:
        if not self.pipeline_use_case:
            raise RuntimeError("Pipeline ainda nao esta configurado. Conclua a etapa de artefatos.")
        self.pipeline_use_case.execute(job_id)

    def requeue_job(self, job_id: str, reason: str, retryable: bool = True) -> Job:
        decision = RetryDecision(job_id=job_id, error_message=reason, retryable=retryable)
        return self.retry_use_case.execute(decision)
