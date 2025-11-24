from __future__ import annotations

import hmac
import hashlib
from fastapi import FastAPI
from fastapi.testclient import TestClient

from application.services.webhook_service import WebhookValidationResult
from interfaces.http.webhook_routes import router as webhook_router
from interfaces.http.dependencies import get_webhook_service, get_app_settings


class _StubWebhookService:
    def __init__(self, secret: str = "secret") -> None:
        self.secret = secret
        self.calls = 0

    def verify(self, payload, signature, integration="external", timestamp_header=None):
        self.calls += 1
        return WebhookValidationResult(trace_id="trace", integration=integration, received_ts=0.0, latency_ms=1.0)

    def snapshot_metrics(self):
        return {"accepted": self.calls, "rejected": 0}


class _StubSettings:
    def __init__(self, env: str = "test") -> None:
        self.app_env = env


def _build_app(webhook_service, settings) -> TestClient:
    app = FastAPI()
    app.dependency_overrides = {
        get_webhook_service: lambda: webhook_service,
        get_app_settings: lambda: settings,
    }
    app.include_router(webhook_router)
    return TestClient(app)


def test_webhook_route_success_returns_trace_id(monkeypatch):
    service = _StubWebhookService()
    settings = _StubSettings(env="test")
    client = _build_app(service, settings)
    payload = b"body"
    sig = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()

    response = client.post(
        "/webhooks/external",
        data=payload,
        headers={"X-Signature": sig, "X-Signature-Timestamp": "0", "X-Integration-Id": "partner"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "received"
    assert body["trace_id"] == "trace"
    assert service.calls == 1


def test_webhook_route_returns_500_with_internal_error(monkeypatch):
    class _FailingService:
        def verify(self, *_args, **_kwargs):
            raise RuntimeError("boom")

        def snapshot_metrics(self):
            return {}

    service = _FailingService()
    settings = _StubSettings(env="production")  # should mask the raw error
    client = _build_app(service, settings)

    response = client.post("/webhooks/external", data=b"body", headers={"X-Signature": "sig", "X-Signature-Timestamp": "1"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Erro interno"
