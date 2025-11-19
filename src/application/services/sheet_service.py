from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from filelock import FileLock

from domain.entities.job import Job
from domain.ports.services import DeliveryLogger

from .ports import SheetGateway


class CsvSheetService(DeliveryLogger):
    """Logs job metadata to CSV and optionally mirrors to Google Sheets."""

    def __init__(self, csv_path: Path, sheet_gateway: Optional[SheetGateway] = None) -> None:
        self.csv_path = csv_path
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.sheet_gateway = sheet_gateway
        self._lock = FileLock(str(self.csv_path) + ".lock")
        self.fieldnames = [
            "job_id",
            "timestamp_utc",
            "source_path",
            "profile",
            "engine",
            "status",
            "language",
            "duration_sec",
            "package_path",
            "version",
        ]
        self._ensure_header()

    def register(self, job: Job, package_path: Path) -> None:
        row = self._build_row(job, package_path)
        self._append_csv(row)
        if self.sheet_gateway:
            self.sheet_gateway.append_row(row)

    def record_job_status(self, job: Job, status: str) -> None:
        row = self._build_row(job, None)
        row["status"] = status
        self._append_csv(row)

    def _build_row(self, job: Job, package_path: Optional[Path]) -> Dict[str, str]:
        return {
            "job_id": job.id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "source_path": str(job.source_path),
            "profile": job.profile_id,
            "engine": job.engine.value,
            "status": job.status.value,
            "language": job.language or "",
            "duration_sec": str(job.duration_sec or ""),
            "package_path": str(package_path) if package_path else "",
            "version": str(job.version),
        }

    def _ensure_header(self) -> None:
        with self._lock:
            if self.csv_path.exists():
                return
            with self.csv_path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
                writer.writeheader()

    def _append_csv(self, row: Dict[str, str]) -> None:
        with self._lock:
            with self.csv_path.open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
                writer.writerow(row)
