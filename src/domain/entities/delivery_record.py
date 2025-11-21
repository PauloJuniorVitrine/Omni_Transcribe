from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class DeliveryRecord:
    """Representa o registro de upload/entrega a servicos externos (GoTranscript/cliente)."""

    job_id: str
    integration: str
    status: str
    external_id: Optional[str] = None
    submitted_at: datetime = field(default_factory=_utcnow)
    message: Optional[str] = None


__all__ = ["DeliveryRecord"]
