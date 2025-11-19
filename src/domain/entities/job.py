from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from .value_objects import ArtifactType, EngineType, JobStatus


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Job:
    """Represents a transcription/translation job tracked throughout the pipeline."""

    id: str
    source_path: Path
    profile_id: str
    status: JobStatus = JobStatus.PENDING
    language: Optional[str] = None
    engine: EngineType = EngineType.OPENAI
    output_paths: Dict[ArtifactType, Path] = field(default_factory=dict)
    metadata: Dict[str, str] = field(default_factory=dict)
    duration_sec: Optional[float] = None
    notes: Optional[str] = None
    version: int = 1
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

    def set_status(self, status: JobStatus, notes: Optional[str] = None) -> None:
        self.status = status
        self.updated_at = _utcnow()
        if notes:
            self.notes = notes

    def attach_artifact(self, artifact_type: ArtifactType, path: Path) -> None:
        self.output_paths[artifact_type] = path
        self.updated_at = _utcnow()

    def bump_version(self) -> int:
        self.version += 1
        self.updated_at = _utcnow()
        return self.version
