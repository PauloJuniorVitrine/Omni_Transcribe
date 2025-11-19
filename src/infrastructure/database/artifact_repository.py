from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

from domain.entities.artifact import Artifact
from domain.ports.repositories import ArtifactRepository

from .serializers import artifact_from_dict, artifact_to_dict
from . import file_storage


class FileArtifactRepository(ArtifactRepository):
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def save_many(self, artifacts: Iterable[Artifact]) -> None:
        stored = self._load_all()
        for artifact in artifacts:
            stored.append(artifact_to_dict(artifact))
        self._save_all(stored)

    def list_by_job(self, job_id: str) -> List[Artifact]:
        stored = self._load_all()
        return [artifact_from_dict(item) for item in stored if item["job_id"] == job_id]

    def _load_all(self) -> List[dict]:
        return file_storage.read_json_list(self.storage_path)

    def _save_all(self, data: List[dict]) -> None:
        file_storage.write_json_list(self.storage_path, data)
