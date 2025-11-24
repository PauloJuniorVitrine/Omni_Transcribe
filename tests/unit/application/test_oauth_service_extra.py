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
