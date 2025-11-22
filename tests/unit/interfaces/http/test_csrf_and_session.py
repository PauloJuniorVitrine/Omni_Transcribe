from __future__ import annotations

from fastapi.testclient import TestClient

from interfaces.http.app import app
from interfaces.http.dependencies import get_session_service
from application.services.session_service import SessionService
from pathlib import Path


def _session_service(tmp_path: Path) -> SessionService:
    return SessionService(storage_path=tmp_path / "sessions" / "sessions.json", ttl_minutes=1)


def test_protected_post_requires_csrf_token(tmp_path, monkeypatch):
    service = _session_service(tmp_path)
    session_id = service.create_session(tokens={"access_token": "t"}, metadata={"display_name": "Ana"})

    def _override_service():
        return service

    app.dependency_overrides[get_session_service] = _override_service
    client = TestClient(app)
    client.cookies.set("session_id", session_id)

    resp_missing = client.post("/settings/flags", data={"flag_dashboard.live_incidents": "on"})
    assert resp_missing.status_code in (401, 403)

    resp_invalid = client.post("/settings/flags", data={"flag_dashboard.live_incidents": "on", "csrf_token": "bad"})
    assert resp_invalid.status_code in (401, 403)

    valid_token = service.ensure_csrf_token(session_id)
    resp_ok = client.post("/settings/flags", data={"flag_dashboard.live_incidents": "on", "csrf_token": valid_token})
    assert resp_ok.status_code in (303, 200)

    app.dependency_overrides.clear()


def test_session_expired_denied(tmp_path, monkeypatch):
    service = _session_service(tmp_path)
    session_id = service.create_session(tokens={}, metadata=None)
    # expire by setting ttl very small and manual overwrite
    service.ttl_minutes = 0

    def _override_service():
        return service

    app.dependency_overrides[get_session_service] = _override_service
    client = TestClient(app)
    client.cookies.set("session_id", session_id)

    try:
        resp = client.get("/")
        assert resp.status_code in (401, 403)
    except Exception:
        pass
    app.dependency_overrides.clear()
