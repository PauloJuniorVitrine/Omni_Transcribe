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
from infrastructure.database import sqlite_repositories


def build_repositories(processing_dir: Path, settings: Settings):
    if getattr(settings, "persistence_backend", "file") == "sqlite":
        db_path = Path(settings.database_url.replace("sqlite:///", ""))
        job_repo = sqlite_repositories.SqlJobRepository(db_path)
        artifact_repo = sqlite_repositories.SqlArtifactRepository(db_path)
        log_repo = sqlite_repositories.SqlLogRepository(db_path)
        review_repo = sqlite_repositories.SqlReviewRepository(db_path)
    else:
        job_repo = FileJobRepository(processing_dir / "jobs.json")
        artifact_repo = FileArtifactRepository(processing_dir / "artifacts.json")
        log_repo = FileLogRepository(processing_dir / "logs.json")
        review_repo = FileReviewRepository(processing_dir / "reviews.json")
    profile_provider = FilesystemProfileProvider(settings.profiles_dir)
    return job_repo, artifact_repo, log_repo, review_repo, profile_provider
