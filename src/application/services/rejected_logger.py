from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from domain.entities.job import Job
from domain.ports.services import RejectedJobLogger


class FilesystemRejectedLogger(RejectedJobLogger):
    """Persists failed job information under rejected/<job_id>/."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def record(self, job: Job, error: str, stage: str, payload: Optional[Dict[str, object]] = None) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        job_dir = self.base_dir / job.id
        job_dir.mkdir(parents=True, exist_ok=True)
        target = job_dir / f"failure_{timestamp}.json"
        body = {
            "job_id": job.id,
            "stage": stage,
            "error": error,
            "status": job.status.value,
            "notes": job.notes,
            "metadata": job.metadata,
            "timestamp_utc": timestamp,
            "payload": payload or {},
        }
        target.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
        return target
