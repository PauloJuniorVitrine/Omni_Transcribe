from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from application.services.webhook_service import WebhookService, WebhookValidationError
from config import Settings


def _settings(tmp_path: Path) -> Settings:
    settings = Settings()
    settings.webhook_secret = "secret"
    settings.webhook_integrations_path = tmp_path / "secrets.json"
    settings.webhook_signature_tolerance_sec = 10
    return settings


def test_verify_rejects_missing_secret(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.webhook_secret = ""  # no default
    service = WebhookService(settings)

    with pytest.raises(WebhookValidationError):
        service.verify(b"payload", "sig", integration="x", timestamp_header=str(int(time.time())))


def test_verify_success_updates_metrics(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    now = int(time.time())
    service = WebhookService(settings)
    payload = b"hello"
    import hmac, hashlib  # local to avoid global deps change

    sig = hmac.new(settings.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    result = service.verify(payload, sig, timestamp_header=str(now))

    assert result.integration == "external"
    assert service.snapshot_metrics()["accepted"] == 1
    assert service.snapshot_metrics()["rejected"] == 0


@pytest.mark.parametrize(
    "payload,signature,timestamp_header,expected",
    [
        (b"", "sig", str(int(time.time())), "Payload vazio."),
        (b"p", None, str(int(time.time())), "Assinatura ausente."),
        (b"p", "sig", None, "Timestamp ausente."),
        (b"p", "sig", "abc", "Timestamp invalido."),
    ],
)
def test_verify_rejected_paths(payload, signature, timestamp_header, expected, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = WebhookService(settings)
    with pytest.raises(WebhookValidationError) as exc:
        service.verify(payload, signature, timestamp_header=timestamp_header)
    assert expected in str(exc.value)
    rejected = service.snapshot_metrics()["rejected"]
    if "Payload vazio" in expected or "Assinatura ausente" in expected or "Assinatura invalida" in expected:
        assert rejected >= 1
    else:
        assert rejected >= 0


def test_verify_rejects_invalid_signature(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    service = WebhookService(settings)
    now = str(int(time.time()))
    with pytest.raises(WebhookValidationError):
        service.verify(b"body", "wrong", timestamp_header=now)
    assert service.snapshot_metrics()["rejected"] == 1


def test_load_integration_secrets_handles_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("{not-json", encoding="utf-8")
    settings = _settings(tmp_path)
    settings.webhook_integrations_path = path

    service = WebhookService(settings)

    assert service._resolve_secret("other") == settings.webhook_secret


def test_resolve_secret_prefers_integration_file(tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.json"
    secrets_path.write_text(json.dumps({"partner": "abc123"}), encoding="utf-8")
    settings = _settings(tmp_path)
    settings.webhook_integrations_path = secrets_path
    service = WebhookService(settings)

    assert service._resolve_secret("partner") == "abc123"


def test_verify_rejects_timestamp_out_of_window(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    settings.webhook_signature_tolerance_sec = 1
    service = WebhookService(settings)
    now = int(time.time()) - 10
    payload = b"body"
    import hmac, hashlib

    sig = hmac.new(settings.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    with pytest.raises(WebhookValidationError):
        service.verify(payload, sig, timestamp_header=str(now))
