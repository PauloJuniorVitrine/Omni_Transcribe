from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from pathlib import Path
import os

import pytest

os.environ.setdefault("CREDENTIALS_SECRET_KEY", "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg=")

from application.services.webhook_service import WebhookService, WebhookValidationError


@dataclass
class DummySettings:
    webhook_secret: str
    webhook_integrations_path: Path
    webhook_signature_tolerance_sec: int


def _build_settings(tmp_path: Path, **overrides) -> DummySettings:
    path = overrides.get("webhook_integrations_path", tmp_path / "integrations.json")
    if not path.exists():
        path.write_text("{}", encoding="utf-8")
    params = {
        "webhook_secret": "base-secret",
        "webhook_integrations_path": path,
        "webhook_signature_tolerance_sec": 60,
    }
    params.update(overrides)
    return DummySettings(**params)


def test_webhook_service_accepts_valid_signature(tmp_path):
    secrets_path = tmp_path / "integrations.json"
    secrets_path.write_text(json.dumps({"custom": "secret-x"}), encoding="utf-8")
    settings = _build_settings(tmp_path, webhook_integrations_path=secrets_path, webhook_secret="")
    service = WebhookService(settings)
    payload = b'{"hello": "world"}'
    signature = hmac.new(b"secret-x", payload, hashlib.sha256).hexdigest()
    timestamp_header = str(int(time.time()))

    result = service.verify(payload, signature, integration="custom", timestamp_header=timestamp_header)

    assert result.integration == "custom"
    assert service.snapshot_metrics() == {"accepted": 1, "rejected": 0}


def test_webhook_service_rejects_missing_signature(tmp_path):
    settings = _build_settings(tmp_path)
    service = WebhookService(settings)
    timestamp_header = str(int(time.time()))

    with pytest.raises(WebhookValidationError):
        service.verify(b"{}", None, timestamp_header=timestamp_header)

    assert service.snapshot_metrics()["rejected"] == 1


def test_webhook_service_rejects_stale_timestamp(tmp_path, monkeypatch):
    settings = _build_settings(tmp_path, webhook_signature_tolerance_sec=5)
    service = WebhookService(settings)
    payload = b"{}"
    signature = hmac.new(settings.webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    now = 1_000_000
    monkeypatch.setattr("application.services.webhook_service.time.time", lambda: now)

    with pytest.raises(WebhookValidationError):
        service.verify(payload, signature, timestamp_header=str(now + 20))


def test_webhook_service_requires_secret(tmp_path):
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("{invalid", encoding="utf-8")
    settings = _build_settings(tmp_path, webhook_integrations_path=bad_json, webhook_secret="")
    service = WebhookService(settings)
    timestamp_header = str(int(time.time()))

    with pytest.raises(WebhookValidationError):
        service.verify(b"{}", "abcd", integration="custom", timestamp_header=timestamp_header)
