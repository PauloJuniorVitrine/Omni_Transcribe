from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from config import Settings


@dataclass(slots=True)
class WebhookValidationResult:
    trace_id: str
    integration: str
    received_ts: float
    latency_ms: float


class WebhookValidationError(Exception):
    """Raised when webhook validation fails."""


class WebhookService:
    """Centralizes webhook signature validation, timing and metrics."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.tolerance_seconds = settings.webhook_signature_tolerance_sec
        self._secrets = self._load_integration_secrets(settings.webhook_integrations_path)
        self._stats: Dict[str, int] = {"accepted": 0, "rejected": 0}

    def verify(
        self,
        payload: bytes,
        signature: str | None,
        *,
        integration: str = "external",
        timestamp_header: str | None,
    ) -> WebhookValidationResult:
        start = time.perf_counter()
        secret = self._resolve_secret(integration)
        if not secret:
            raise WebhookValidationError(f"Segredo não configurado para integração {integration}.")
        if not payload:
            self._stats["rejected"] += 1
            raise WebhookValidationError("Payload vazio.")
        if not signature:
            self._stats["rejected"] += 1
            raise WebhookValidationError("Assinatura ausente.")
        self._validate_timestamp(timestamp_header)
        computed = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, signature):
            self._stats["rejected"] += 1
            raise WebhookValidationError("Assinatura inválida.")
        trace_id = uuid.uuid4().hex
        latency_ms = (time.perf_counter() - start) * 1000
        self._stats["accepted"] += 1
        return WebhookValidationResult(
            trace_id=trace_id,
            integration=integration,
            received_ts=time.time(),
            latency_ms=latency_ms,
        )

    def snapshot_metrics(self) -> Dict[str, int]:
        return dict(self._stats)

    def _validate_timestamp(self, timestamp_header: str | None) -> None:
        if not timestamp_header:
            raise WebhookValidationError("Timestamp ausente.")
        try:
            ts = int(timestamp_header)
        except ValueError as exc:
            raise WebhookValidationError("Timestamp inválido.") from exc
        now = int(time.time())
        if abs(now - ts) > self.tolerance_seconds:
            raise WebhookValidationError("Timestamp fora da janela permitida.")

    def _resolve_secret(self, integration: str) -> str:
        return self._secrets.get(integration) or self.settings.webhook_secret

    @staticmethod
    def _load_integration_secrets(path: Path) -> Dict[str, str]:
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        return {str(key): str(value) for key, value in data.items() if value}


__all__ = ["WebhookService", "WebhookValidationError", "WebhookValidationResult"]
