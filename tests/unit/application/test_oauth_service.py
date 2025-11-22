from __future__ import annotations

import types

from application.services.oauth_service import OAuthService
from config.settings import Settings


class _StubResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self) -> None:  # pragma: no cover - nothing to do
        return

    def json(self) -> dict:
        return self._payload


def test_build_authorization_url_includes_params(monkeypatch):
    monkeypatch.setenv("OAUTH_AUTHORIZE_URL", "https://auth.example/authorize")
    monkeypatch.setenv("OAUTH_CLIENT_ID", "client")
    monkeypatch.setenv("OAUTH_REDIRECT_URI", "https://app/callback")
    settings = Settings()
    svc = OAuthService(settings)
    data = svc.build_authorization_url(scope="openid email")

    assert data["url"].startswith(settings.oauth_authorize_url)
    assert "client_id=client" in data["url"]
    assert "scope=openid%20email" in data["url"]
    assert data["state"]


def test_exchange_code_posts_payload(monkeypatch):
    monkeypatch.setenv("OAUTH_TOKEN_URL", "https://auth.example/token")
    monkeypatch.setenv("OAUTH_CLIENT_ID", "id")
    monkeypatch.setenv("OAUTH_CLIENT_SECRET", "secret")
    monkeypatch.setenv("OAUTH_REDIRECT_URI", "https://app/callback")
    captured = {}

    def fake_post(url, data, timeout):  # noqa: ANN001
        captured["url"] = url
        captured["data"] = data
        captured["timeout"] = timeout
        return _StubResponse({"access_token": "token123"})

    monkeypatch.setattr("application.services.oauth_service.requests", types.SimpleNamespace(post=fake_post))
    settings = Settings()
    svc = OAuthService(settings)

    payload = svc.exchange_code("abc123")

    assert payload["access_token"] == "token123"
    assert captured["url"] == settings.oauth_token_url
    assert captured["data"]["code"] == "abc123"
    assert captured["data"]["client_secret"] == "secret"
