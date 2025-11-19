from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .value_objects import ArtifactType


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Artifact:
    """Represents an output artifact (TXT, SRT, VTT, JSON, ZIP)."""

    id: str
    job_id: str
    artifact_type: ArtifactType
    path: Path
    version: int = 1
    created_at: datetime = field(default_factory=_utcnow)
