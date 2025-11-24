from __future__ import annotations

import pytest

from application.services.oauth_service import OAuthService
from config import Settings


def test_build_authorization_url_generates_state_and_defaults_scope(monkeypatch) -> None:
    settings = Settings()
    settings.oauth_authorize_url = "https://auth.example.com/authorize"
    settings.oauth_client_id = "cid"
    settings.oauth_redirect_uri = "https://app/callback"
    service = OAuthService(settings)
    monkeypatch.setattr("application.services.oauth_service.secrets.token_urlsafe", lambda n=16: "state123")

    payload = service.build_authorization_url()

    assert payload["state"] == "state123"
    assert "scope=openid%20email%20profile" in payload["url"]


def test_build_authorization_url_raises_when_missing_config() -> None:
    service = OAuthService(Settings())
    with pytest.raises(RuntimeError):
        service.build_authorization_url()
