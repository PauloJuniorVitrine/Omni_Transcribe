from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from domain.entities.artifact import Artifact
from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.user_review import UserReview
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus, LogLevel, ReviewDecision


def _serialize_datetime(value: datetime) -> str:
    return value.isoformat()


def _deserialize_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def job_to_dict(job: Job) -> Dict[str, Any]:
    return {
        "id": job.id,
        "source_path": str(job.source_path),
        "profile_id": job.profile_id,
        "status": job.status.value,
        "language": job.language,
        "engine": job.engine.value,
        "output_paths": {key.value: str(path) for key, path in job.output_paths.items()},
        "metadata": job.metadata,
        "duration_sec": job.duration_sec,
        "notes": job.notes,
        "version": job.version,
        "created_at": _serialize_datetime(job.created_at),
        "updated_at": _serialize_datetime(job.updated_at),
    }


def job_from_dict(payload: Dict[str, Any]) -> Job:
    return Job(
        id=payload["id"],
        source_path=Path(payload["source_path"]),
        profile_id=payload["profile_id"],
        status=JobStatus(payload["status"]),
        language=payload.get("language"),
        engine=EngineType(payload["engine"]),
        output_paths={ArtifactType(key): Path(value) for key, value in (payload.get("output_paths") or {}).items()},
        metadata=payload.get("metadata") or {},
        duration_sec=payload.get("duration_sec"),
        notes=payload.get("notes"),
        version=int(payload.get("version", 1)),
        created_at=_deserialize_datetime(payload["created_at"]),
        updated_at=_deserialize_datetime(payload["updated_at"]),
    )


def artifact_to_dict(artifact: Artifact) -> Dict[str, Any]:
    return {
        "id": artifact.id,
        "job_id": artifact.job_id,
        "artifact_type": artifact.artifact_type.value,
        "path": str(artifact.path),
        "version": artifact.version,
        "created_at": _serialize_datetime(artifact.created_at),
    }


def artifact_from_dict(payload: Dict[str, Any]) -> Artifact:
    return Artifact(
        id=payload["id"],
        job_id=payload["job_id"],
        artifact_type=ArtifactType(payload["artifact_type"]),
        path=Path(payload["path"]),
        version=int(payload.get("version", 1)),
        created_at=_deserialize_datetime(payload["created_at"]),
    )


def logentry_to_dict(entry: LogEntry) -> Dict[str, Any]:
    return {
        "job_id": entry.job_id,
        "event": entry.event,
        "level": entry.level.value,
        "message": entry.message,
        "timestamp": _serialize_datetime(entry.timestamp),
    }


def logentry_from_dict(payload: Dict[str, Any]) -> LogEntry:
    return LogEntry(
        job_id=payload["job_id"],
        event=payload["event"],
        level=LogLevel(payload["level"]),
        message=payload.get("message"),
        timestamp=_deserialize_datetime(payload["timestamp"]),
    )


def review_to_dict(review: UserReview) -> Dict[str, Any]:
    return {
        "id": review.id,
        "job_id": review.job_id,
        "reviewer": review.reviewer,
        "decision": review.decision.value,
        "notes": review.notes,
        "timestamp": _serialize_datetime(review.timestamp),
    }


def review_from_dict(payload: Dict[str, Any]) -> UserReview:
    return UserReview(
        id=payload["id"],
        job_id=payload["job_id"],
        reviewer=payload["reviewer"],
        decision=ReviewDecision(payload["decision"]),
        notes=payload.get("notes"),
        timestamp=_deserialize_datetime(payload["timestamp"]),
    )
