from __future__ import annotations

from pathlib import Path
from typing import Tuple

from config import Settings
from domain.ports.services import RejectedJobLogger
from infrastructure.database.artifact_repository import FileArtifactRepository
from infrastructure.database.job_repository import FileJobRepository
from infrastructure.database.log_repository import FileLogRepository
from infrastructure.database.profile_provider import FilesystemProfileProvider
from infrastructure.database.review_repository import FileReviewRepository


def build_repositories(processing_dir: Path, settings: Settings):
    job_repo = FileJobRepository(processing_dir / "jobs.json")
    artifact_repo = FileArtifactRepository(processing_dir / "artifacts.json")
    log_repo = FileLogRepository(processing_dir / "logs.json")
    review_repo = FileReviewRepository(processing_dir / "reviews.json")
    profile_provider = FilesystemProfileProvider(settings.profiles_dir)
    return job_repo, artifact_repo, log_repo, review_repo, profile_provider
