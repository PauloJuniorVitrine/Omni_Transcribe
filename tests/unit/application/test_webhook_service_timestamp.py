from __future__ import annotations

import time

import pytest

from application.services.webhook_service import WebhookService, WebhookValidationError
from config import Settings


def _settings() -> Settings:
    s = Settings()
    s.webhook_secret = "secret"
    s.webhook_signature_tolerance_sec = 1
    return s


def test_verify_rejects_missing_timestamp() -> None:
    service = WebhookService(_settings())
    with pytest.raises(WebhookValidationError):
        service.verify(b"body", "sig", timestamp_header=None)


def test_verify_rejects_outside_tolerance() -> None:
    service = WebhookService(_settings())
    now = int(time.time()) - 100
    with pytest.raises(WebhookValidationError):
        service.verify(b"body", "sig", timestamp_header=str(now))
