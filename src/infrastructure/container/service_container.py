from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from application.logging_config import configure_logging
from config import Settings, get_settings
from domain.entities.job import Job
from domain.ports.services import ArtifactBuilder
from domain.usecases.generate_artifacts import GenerateArtifacts
from domain.usecases.pipeline import ProcessJobPipeline
from domain.usecases.register_delivery import RegisterDelivery

from application.services.oauth_service import OAuthService
from application.services.delivery_template_service import DeliveryTemplateRegistry
from application.services.accuracy_service import TranscriptionAccuracyGuard
from infrastructure.telemetry.metrics_logger import notify_alert, record_metric
from . import components_artifacts, components_asr, components_delivery, components_storage


@dataclass
class ServiceContainer:
    """Centralized dependency container for CLI, HTTP API and workers."""

    settings: Settings = field(default_factory=get_settings)

    def __post_init__(self) -> None:
        self.settings.ensure_runtime_directories()
        configure_logging()
        processing_dir = Path(self.settings.base_processing_dir)
        processing_dir.mkdir(parents=True, exist_ok=True)

        (
            self.job_repository,
            self.artifact_repository,
            self.log_repository,
            self.review_repository,
            self.profile_provider,
        ) = components_storage.build_repositories(processing_dir, self.settings)

        (
            self.sheet_service,
            self.status_publisher,
            self.rejected_logger,
        ) = components_delivery.build_logging_and_sheet(self.settings)

        templates_dir = Path(self.settings.profiles_dir) / "templates"
        self.template_registry = DeliveryTemplateRegistry(templates_dir)

        core_tuple = components_asr.build_core_usecases(
            settings=self.settings,
            job_repository=self.job_repository,
            profile_provider=self.profile_provider,
            log_repository=self.log_repository,
            review_repository=self.review_repository,
            sheet_service=self.sheet_service,
            status_publisher=self.status_publisher,
            rejected_logger=self.rejected_logger,
        )
        (
            self.create_job_use_case,
            self.run_asr_use_case,
            self.post_edit_use_case,
            self.retry_use_case,
            self.handle_review_use_case,
            self.asr_service,
            self.post_edit_service,
        ) = core_tuple

        self.artifact_builder: Optional[ArtifactBuilder] = None
        self.generate_artifacts_use_case: Optional[GenerateArtifacts] = None
        self.pipeline_use_case: Optional[ProcessJobPipeline] = None
        self.package_service: Optional[components_delivery.ZipPackageService] = None  # type: ignore[attr-defined]
        self.register_delivery_use_case: Optional[RegisterDelivery] = None
        self._reference_cache: Dict[str, Optional[str]] = {}
        self.accuracy_guard = TranscriptionAccuracyGuard(
            job_repository=self.job_repository,
            log_repository=self.log_repository,
            threshold=getattr(self.settings, "accuracy_threshold", 0.99),
            reference_loader=self._load_reference_transcript,
            metric_dispatcher=record_metric,
            alert_dispatcher=notify_alert,
        )

        self._wire_artifacts_pipeline()
        self.oauth_service = OAuthService(self.settings)

    def wire_artifact_builder(self, builder: ArtifactBuilder) -> None:
        self.artifact_builder = builder
        self.generate_artifacts_use_case = components_artifacts.build_generate_artifacts(
            builder=builder,
            job_repository=self.job_repository,
            artifact_repository=self.artifact_repository,
            log_repository=self.log_repository,
            profile_provider=self.profile_provider,
            status_publisher=self.status_publisher,
        )
        self.pipeline_use_case = ProcessJobPipeline(
            asr_use_case=self.run_asr_use_case,
            post_edit_use_case=self.post_edit_use_case,
            artifact_use_case=self.generate_artifacts_use_case,
            log_repository=self.log_repository,
            retry_handler=self.retry_use_case,
            accuracy_guard=self.accuracy_guard,
        )

    def _wire_artifacts_pipeline(self) -> None:
        builder = components_artifacts.build_default_builder(self.settings, self.template_registry)
        self.wire_artifact_builder(builder)
        self.package_service, self.register_delivery_use_case = components_delivery.build_delivery_services(
            self.settings,
            self.job_repository,
            self.artifact_repository,
            self.sheet_service,
            self.log_repository,
        )

    def _load_reference_transcript(self, job: Job) -> Optional[str]:
        metadata = job.metadata or {}
        inline = metadata.get("reference_transcript")
        if inline:
            return inline
        explicit_path = metadata.get("reference_path")
        if explicit_path:
            try:
                return Path(explicit_path).read_text(encoding="utf-8")
            except OSError:
                return None
        cache_key = job.profile_id
        if cache_key in self._reference_cache:
            return self._reference_cache[cache_key]
        reference_root = Path(self.settings.profiles_dir) / "references"
        candidates = [
            reference_root / f"{job.profile_id}.txt",
            Path(self.settings.profiles_dir) / job.profile_id / "reference.txt",
            Path(self.settings.profiles_dir) / f"{job.profile_id}.reference.txt",
        ]
        reference_text: Optional[str] = None
        for path in candidates:
            if path.is_file():
                try:
                    reference_text = path.read_text(encoding="utf-8")
                    break
                except OSError:
                    continue
        self._reference_cache[cache_key] = reference_text
        return reference_text


def get_container() -> ServiceContainer:
    if getattr(get_container, "_instance", None) is None:
        get_container._instance = ServiceContainer()
    return get_container._instance
