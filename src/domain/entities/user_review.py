from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from .value_objects import ReviewDecision


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserReview:
    """Represents the human review decision on a job."""

    id: str
    job_id: str
    reviewer: str
    decision: ReviewDecision
    notes: Optional[str] = None
    timestamp: datetime = field(default_factory=_utcnow)
