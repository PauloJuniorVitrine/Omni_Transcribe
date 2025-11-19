from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .value_objects import LogLevel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class LogEntry:
    """Structured operational log entry."""

    job_id: str
    event: str
    level: LogLevel = LogLevel.INFO
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=_utcnow)
