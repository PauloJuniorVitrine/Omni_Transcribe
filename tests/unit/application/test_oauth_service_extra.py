from __future__ import annotations

import pytest

from application.services.oauth_service import OAuthService
from config import Settings


def test_build_authorization_url_requires_config() -> None:
    settings = Settings()
    settings.oauth_authorize_url = ""
    service = OAuthService(settings)
    with pytest.raises(RuntimeError):
        service.build_authorization_url()


def test_exchange_code_propagates_http_error(monkeypatch) -> None:
    class _Resp:
        def raise_for_status(self):
            raise RuntimeError("boom")

    def _post(_url, data=None, timeout=None):
        return _Resp()

    settings = Settings()
    settings.oauth_token_url = "http://example"
    service = OAuthService(settings)
    monkeypatch.setattr("application.services.oauth_service.requests.post", _post)

    with pytest.raises(RuntimeError):
        service.exchange_code("code123")


def test_exchange_code_raises_when_not_configured() -> None:
    settings = Settings()
    settings.oauth_token_url = ""
    service = OAuthService(settings)
    with pytest.raises(RuntimeError):
        service.exchange_code("any")


def test_build_authorization_url_generates_state_and_encodes_scope(monkeypatch) -> None:
    settings = Settings()
    settings.oauth_authorize_url = "https://auth.example.com/authorize"
    settings.oauth_client_id = "client"
    settings.oauth_redirect_uri = "https://app/callback"
    service = OAuthService(settings)
    monkeypatch.setattr("application.services.oauth_service.secrets.token_urlsafe", lambda n=16: "STATE123")

    payload = service.build_authorization_url(scope="openid email")

    assert payload["state"] == "STATE123"
    assert "scope=openid%20email" in payload["url"]
    assert payload["url"].startswith(settings.oauth_authorize_url)


def test_exchange_code_success(monkeypatch) -> None:
    class _Resp:
        def __init__(self):
            self.called = False

        def raise_for_status(self):
            self.called = True

        def json(self):
            return {"access_token": "token"}

    def _post(url, data=None, timeout=None):
        return _Resp()

    settings = Settings()
    settings.oauth_token_url = "https://auth.example.com/token"
    settings.oauth_client_id = "client"
    settings.oauth_client_secret = "secret"
    settings.oauth_redirect_uri = "https://app/callback"
    service = OAuthService(settings)
    monkeypatch.setattr("application.services.oauth_service.requests.post", _post)

    result = service.exchange_code("CODE")

    assert result["access_token"] == "token"
