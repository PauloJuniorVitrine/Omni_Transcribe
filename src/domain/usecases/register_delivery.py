from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from ..entities.artifact import Artifact
from ..entities.delivery_record import DeliveryRecord
from ..entities.job import Job
from ..entities.log_entry import LogEntry
from ..entities.value_objects import JobStatus, LogLevel
from ..ports.repositories import ArtifactRepository, JobRepository, LogRepository
from ..ports.services import DeliveryClient, DeliveryLogger, PackageService


class RegisterDelivery:
    """Create the delivery package and log the outcome."""

    def __init__(
        self,
        job_repository: JobRepository,
        artifact_repository: ArtifactRepository,
        package_service: PackageService,
        delivery_logger: DeliveryLogger,
        log_repository: LogRepository,
        delivery_client: Optional[DeliveryClient] = None,
    ) -> None:
        self.job_repository = job_repository
        self.artifact_repository = artifact_repository
        self.package_service = package_service
        self.delivery_logger = delivery_logger
        self.log_repository = log_repository
        self.delivery_client = delivery_client

    def execute(self, job_id: str) -> Path:
        job = self.job_repository.find_by_id(job_id)
        if not job:
            raise ValueError(f"Job {job_id} nao encontrado")
        if job.status != JobStatus.APPROVED:
            raise ValueError("Job precisa estar aprovado para gerar pacote de entrega.")

        artifacts: Iterable[Artifact] = self.artifact_repository.list_by_job(job.id)
        artifacts_list = list(artifacts)
        if not artifacts_list:
            raise ValueError("Nenhum artefato disponivel para empacotar.")

        package_path = self.package_service.create_package(job, artifacts_list)
        self.delivery_logger.register(job, package_path)
        self.log_repository.append(
            LogEntry(
                job_id=job.id,
                event="delivery_package_created",
                level=LogLevel.INFO,
                message=f"Pacote gerado em {package_path}",
            )
        )
        if self.delivery_client:
            record = self._submit_external(job, package_path)
            self._log_external_submission(job.id, record)
        return package_path

    def _submit_external(self, job: Job, package_path: Path) -> DeliveryRecord:
        if not self.delivery_client:
            raise RuntimeError("delivery_client not configured.")
        return self.delivery_client.submit_package(job, package_path)

    def _log_external_submission(self, job_id: str, record: DeliveryRecord) -> None:
        self.log_repository.append(
            LogEntry(
                job_id=job_id,
                event="delivery_external_submitted",
                level=LogLevel.INFO,
                message=f"{record.integration} status={record.status}",
            )
        )
