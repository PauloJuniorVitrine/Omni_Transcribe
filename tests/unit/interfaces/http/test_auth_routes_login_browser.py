from __future__ import annotations

from fastapi.testclient import TestClient

from interfaces.http.app import app


class _OAuth:
    def build_authorization_url(self):
        return {"url": "https://auth.example.com", "state": "s"}


def test_auth_login_browser_redirect(monkeypatch):
    app.dependency_overrides.clear()
    from interfaces.http import auth_routes
    from interfaces.http.dependencies import get_app_settings

    app.dependency_overrides[auth_routes.get_oauth_service] = lambda: _OAuth()
    client = TestClient(app)
    resp = client.get("/auth/login/browser", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"].startswith("https://auth.example.com")
    app.dependency_overrides.clear()
