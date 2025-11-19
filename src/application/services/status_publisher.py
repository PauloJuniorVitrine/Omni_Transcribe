from __future__ import annotations

from __future__ import annotations

import logging

from domain.entities.job import Job
from domain.ports.services import JobStatusPublisher

from .sheet_service import CsvSheetService

logger = logging.getLogger(__name__)


class SheetStatusPublisher(JobStatusPublisher):
    """Adapter that writes job status updates to the sheet/CSV service."""

    def __init__(self, sheet_service: CsvSheetService) -> None:
        self.sheet_service = sheet_service

    def publish(self, job: Job) -> None:
        try:
            self.sheet_service.record_job_status(job, job.status.value)
        except Exception as exc:  # pragma: no cover - logged for operational visibility
            logger.warning("Falha ao registrar job %s na planilha: %s", job.id, exc)
