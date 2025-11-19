from __future__ import annotations

from pathlib import Path
from typing import List

from domain.entities.log_entry import LogEntry
from domain.ports.repositories import LogRepository

from .serializers import logentry_from_dict, logentry_to_dict
from . import file_storage


class FileLogRepository(LogRepository):
    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self.storage_path.write_text("[]", encoding="utf-8")

    def append(self, entry: LogEntry) -> None:
        data = self._load_all()
        data.append(logentry_to_dict(entry))
        self._save_all(data)

    def list_by_job(self, job_id: str) -> List[LogEntry]:
        data = self._load_all()
        return [logentry_from_dict(item) for item in data if item["job_id"] == job_id]

    def list_recent(self, limit: int = 20) -> List[LogEntry]:
        data = self._load_all()
        entries = [logentry_from_dict(item) for item in data]
        entries.sort(key=lambda entry: entry.timestamp, reverse=True)
        return entries[:limit]

    def _load_all(self) -> List[dict]:
        return file_storage.read_json_list(self.storage_path)

    def _save_all(self, data: List[dict]) -> None:
        file_storage.write_json_list(self.storage_path, data)
