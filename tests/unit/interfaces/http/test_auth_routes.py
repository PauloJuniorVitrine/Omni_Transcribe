from __future__ import annotations

from fastapi.testclient import TestClient

from interfaces.http.app import app
from interfaces.http import auth_routes
from interfaces.http.dependencies import get_session_service
from application.services.session_service import SessionService
from pathlib import Path


class _StubOAuthService:
    def __init__(self) -> None:
        self.exchanged = []

    def build_authorization_url(self, state=None, scope="openid email profile"):  # noqa: ANN001
        return {"url": "https://auth.local/authorize?state=stub", "state": state or "stub-state"}

    def exchange_code(self, code: str) -> dict:
        self.exchanged.append(code)
        return {"access_token": "tok-" + code}


def _session_service(tmp_path: Path) -> SessionService:
    return SessionService(storage_path=tmp_path / "sessions" / "sessions.json", ttl_minutes=1)


def test_login_and_callback_sets_session_cookie(tmp_path):
    oauth_stub = _StubOAuthService()
    session_service = _session_service(tmp_path)

    app.dependency_overrides[auth_routes.get_oauth_service] = lambda: oauth_stub
    app.dependency_overrides[get_session_service] = lambda: session_service

    client = TestClient(app)

    resp_login = client.get("/auth/login")
    assert resp_login.status_code == 200
    assert "url" in resp_login.json()

    resp_callback = client.get("/auth/callback", params={"code": "abc", "state": "xyz"}, headers={"accept": "application/json"})
    assert resp_callback.status_code == 200
    assert resp_callback.json()["tokens"]["access_token"] == "tok-abc"
    assert "session_id" in resp_callback.cookies

    app.dependency_overrides.clear()
