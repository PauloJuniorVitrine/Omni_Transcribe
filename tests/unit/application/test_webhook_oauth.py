from __future__ import annotations

import hashlib
import hmac
import time
from types import SimpleNamespace

import requests

from application.services.oauth_service import OAuthService
from application.services.webhook_service import WebhookService, WebhookValidationError
from config.settings import Settings


def _prepare_settings(tmp_path):
    settings = Settings()
    settings.webhook_secret = "webhook-secret"
    settings.webhook_integrations_path = tmp_path / "integrations.json"
    settings.webhook_integrations_path.write_text("{}", encoding="utf-8")
    return settings


def test_webhook_service_verify_accepts(tmp_path):
    settings = _prepare_settings(tmp_path)
    service = WebhookService(settings=settings)
    payload = b'{"foo": "bar"}'
    timestamp = str(int(time.time()))
    signature = hmac.new(settings.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    result = service.verify(payload, signature, timestamp_header=timestamp)
    assert result.integration == "external"


def test_webhook_service_rejects_bad_signature(tmp_path):
    settings = _prepare_settings(tmp_path)
    service = WebhookService(settings=settings)
    payload = b"{}"
    timestamp = str(int(time.time()))
    try:
        service.verify(payload, "bad", timestamp_header=timestamp)
    except WebhookValidationError as exc:
        assert "Assinatura invalida" in str(exc)
    else:
        raise AssertionError("WebhookValidationError esperado")


def test_oauth_service_build_url():
    settings = Settings()
    settings.oauth_authorize_url = "https://auth.example.com/oauth/authorize"
    settings.oauth_client_id = "client"
    settings.oauth_redirect_uri = "https://app/callback"
    service = OAuthService(settings=settings)
    result = service.build_authorization_url(state="abc")
    assert "https://auth.example.com/oauth/authorize" in result["url"]


def test_oauth_service_exchange_code(monkeypatch):
    settings = Settings()
    settings.oauth_token_url = "https://auth.example.com/oauth/token"
    settings.oauth_client_id = "client"
    settings.oauth_client_secret = "secret"
    settings.oauth_redirect_uri = "https://app/callback"
    response = SimpleNamespace()
    response.status_code = 200
    response.json = lambda: {"access_token": "ok"}
    response.raise_for_status = lambda: None
    def fake_post(url, data, timeout):
        assert url == settings.oauth_token_url
        return response
    monkeypatch.setattr(requests, "post", fake_post)
    service = OAuthService(settings=settings)
    tokens = service.exchange_code("code")
    assert tokens["access_token"] == "ok"
