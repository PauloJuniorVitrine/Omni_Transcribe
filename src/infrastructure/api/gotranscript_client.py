from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import requests

from domain.entities.delivery_record import DeliveryRecord
from domain.entities.job import Job
from domain.ports.services import DeliveryClient


class GoTranscriptClient(DeliveryClient):
    """HTTP client responsible for sending ZIP packages to GoTranscript endpoints."""

    def __init__(self, base_url: str, api_key: str, timeout: int = 30) -> None:
        if not api_key:
            raise ValueError("GOTRANSCRIPT_API_KEY nao configurado.")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()

    def submit_package(self, job: Job, package_path: Path) -> DeliveryRecord:
        url = f"{self.base_url}/deliveries"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        data: Dict[str, Any] = {
            "job_id": job.id,
            "profile": job.profile_id,
            "version": job.version,
        }
        metadata = job.metadata or {}
        for key, value in metadata.items():
            data[f"meta[{key}]"] = value

        with package_path.open("rb") as fp:
            files = {"package": (package_path.name, fp, "application/zip")}
            response = self.session.post(url, headers=headers, data=data, files=files, timeout=self.timeout)
        response.raise_for_status()
        body: Dict[str, Any] = response.json()
        return DeliveryRecord(
            job_id=job.id,
            integration="gotranscript",
            status=str(body.get("status", "submitted")),
            external_id=_extract_external_id(body),
            message=body.get("message"),
        )


def _extract_external_id(body: Dict[str, Any]) -> Optional[str]:
    for key in ("id", "delivery_id", "reference"):
        value = body.get(key)
        if value is not None:
            return str(value)
    return None


__all__ = ["GoTranscriptClient"]
