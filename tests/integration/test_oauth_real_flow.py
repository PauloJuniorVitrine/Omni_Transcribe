from __future__ import annotations

from types import SimpleNamespace
from fastapi.testclient import TestClient

from interfaces.http.app import app
import interfaces.http.auth_routes as auth_routes
import interfaces.http.app as http_app


class _StubOAuthService:
    def __init__(self):
        self.state = "e2e-state"
        self.tokens = {"access_token": "t123", "refresh_token": "r456"}

    def build_authorization_url(self):
        return {"url": "https://auth.example.com/authorize", "state": self.state}

    def exchange_code(self, code: str):
        assert code == "test-code"
        return self.tokens


class _StubSessionService:
    def __init__(self):
        self.sessions = {}
        self.ttl_seconds = 3600

    def create_session(self, tokens, metadata=None):
        sid = "sess-123"
        self.sessions[sid] = {"tokens": tokens, "metadata": metadata or {}}
        return sid


def _override_settings(monkeypatch):
    settings = SimpleNamespace(
        oauth_client_id="client",
        oauth_client_secret="secret",
        oauth_authorize_url="https://auth.example.com/authorize",
        oauth_token_url="https://auth.example.com/token",
        oauth_redirect_uri="https://app.example.com/callback",
        session_ttl_minutes=30,
        app_env="test",
        max_request_body_mb=25,
        base_input_dir="inbox",
        base_output_dir="output",
        base_processing_dir="processing/tests",
        base_backup_dir="backup",
        base_rejected_dir="rejected",
        csv_log_path="output/log.csv",
        feature_flags={"ui.api_settings": True},
    )
    monkeypatch.setattr(http_app, "_app_settings", settings, raising=False)
    monkeypatch.setattr(http_app, "get_settings", lambda: settings)
    return settings


def test_oauth_flow_end_to_end_with_stub(monkeypatch):
    _override_settings(monkeypatch)
    oauth_stub = _StubOAuthService()
    session_stub = _StubSessionService()
    app.dependency_overrides[auth_routes.get_oauth_service] = lambda: oauth_stub
    app.dependency_overrides[auth_routes.get_session_service] = lambda: session_stub

    client = TestClient(app)
    login = client.get("/auth/login")
    assert login.status_code == 200
    payload = login.json()
    assert payload["state"] == oauth_stub.state
    assert payload["url"].startswith("https://auth.example.com/authorize")

    callback = client.get(
        "/auth/callback",
        params={"code": "test-code", "state": oauth_stub.state},
        headers={"accept": "application/json"},
    )
    assert callback.status_code == 200
    body = callback.json()
    assert body["tokens"]["access_token"] == "t123"
    assert "session_id" in callback.cookies

    app.dependency_overrides.clear()
