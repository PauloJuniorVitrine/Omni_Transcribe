from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional
from zipfile import ZIP_DEFLATED, ZipFile

from domain.entities.artifact import Artifact
from domain.entities.job import Job
from domain.ports.services import PackageService, StorageClient


class ZipPackageService(PackageService):
    """Creates delivery ZIPs and mirrors them to optional storage."""

    def __init__(self, backup_dir: Path, storage_client: Optional[StorageClient] = None) -> None:
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.storage_client = storage_client

    def create_package(self, job: Job, artifacts: Iterable[Artifact]) -> Path:
        job_backup_dir = self.backup_dir / job.id
        job_backup_dir.mkdir(parents=True, exist_ok=True)
        package_path = job_backup_dir / f"{job.id}_v{job.version}.zip"
        with ZipFile(package_path, "w", compression=ZIP_DEFLATED) as zip_file:
            for artifact in artifacts:
                arcname = f"{job.id}/{artifact.path.name}"
                zip_file.write(artifact.path, arcname=arcname)

        if self.storage_client:
            remote_key = f"{job.id}/{package_path.name}"
            self.storage_client.upload(package_path, remote_key)
        return package_path
