from __future__ import annotations

from pathlib import Path

from application.services.artifact_builder import FilesystemArtifactBuilder
from application.services.subtitle_formatter import SubtitleFormatter
from application.services.validator_service import TranscriptValidator
from application.services.delivery_template_service import DeliveryTemplateRegistry
from config import Settings
from domain.usecases.generate_artifacts import GenerateArtifacts


def build_default_builder(settings: Settings, template_registry: DeliveryTemplateRegistry | None = None) -> FilesystemArtifactBuilder:
    return FilesystemArtifactBuilder(
        Path(settings.base_output_dir),
        SubtitleFormatter(),
        TranscriptValidator(),
        template_registry=template_registry,
    )


def build_generate_artifacts(
    builder,
    job_repository,
    artifact_repository,
    log_repository,
    profile_provider,
    status_publisher,
):
    return GenerateArtifacts(
        job_repository=job_repository,
        artifact_repository=artifact_repository,
        artifact_builder=builder,
        log_repository=log_repository,
        profile_provider=profile_provider,
        status_publisher=status_publisher,
    )
