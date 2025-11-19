from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from domain.entities.job import Job
from domain.ports.repositories import JobRepository

from .serializers import job_from_dict, job_to_dict
from . import file_storage


class FileJobRepository(JobRepository):
    """Simple JSON-file backed repository suitable for the initial iteration."""

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def create(self, job: Job) -> Job:
        jobs = self._load_all()
        jobs.append(job_to_dict(job))
        self._save_all(jobs)
        return job

    def update(self, job: Job) -> Job:
        jobs = self._load_all()
        updated = False
        for idx, existing in enumerate(jobs):
            if existing["id"] == job.id:
                jobs[idx] = job_to_dict(job)
                updated = True
                break
        if not updated:
            jobs.append(job_to_dict(job))
        self._save_all(jobs)
        return job

    def find_by_id(self, job_id: str) -> Optional[Job]:
        jobs = self._load_all()
        for data in jobs:
            if data["id"] == job_id:
                return job_from_dict(data)
        return None

    def list_recent(self, limit: int = 50) -> List[Job]:
        jobs = self._load_all()
        sorted_jobs = sorted(jobs, key=lambda item: item["updated_at"], reverse=True)
        return [job_from_dict(item) for item in sorted_jobs[:limit]]

    def _load_all(self) -> List[Dict]:
        return file_storage.read_json_list(self.storage_path)

    def _save_all(self, jobs: List[Dict]) -> None:
        file_storage.write_json_list(self.storage_path, jobs)
