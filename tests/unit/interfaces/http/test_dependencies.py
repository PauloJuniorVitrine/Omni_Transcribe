from __future__ import annotations

from types import SimpleNamespace
import os

import pytest
from fastapi import HTTPException
from starlette.requests import Request

os.environ.setdefault("CREDENTIALS_SECRET_KEY", "eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHg=")

from interfaces.http import dependencies


def _make_request(method: str = "GET", headers: list[tuple[bytes, bytes]] | None = None, cookies: dict | None = None):
    headers = headers or []
    if cookies:
        cookie_pairs = "; ".join(f"{key}={value}" for key, value in cookies.items())
        headers.append((b"cookie", cookie_pairs.encode("utf-8")))

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {"type": "http", "method": method, "path": "/", "headers": headers}
    return Request(scope, receive)


@pytest.fixture(autouse=True)
def disable_test_mode(monkeypatch):
    monkeypatch.setenv("TEST_MODE", "0")
    monkeypatch.setenv("OMNI_TEST_MODE", "0")
    settings = SimpleNamespace(app_env="development", test_mode=False)
    monkeypatch.setattr(dependencies, "get_app_settings", lambda: settings)


def test_get_webhook_service_caches_instances(tmp_path, monkeypatch):
    dependencies._webhook_service_cache.clear()
    settings = SimpleNamespace(
        webhook_secret="secret-1",
        webhook_signature_tolerance_sec=60,
        webhook_integrations_path=tmp_path / "integrations.json",
    )
    settings.webhook_integrations_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(dependencies, "get_app_settings", lambda: settings)

    first = dependencies.get_webhook_service()
    second = dependencies.get_webhook_service()
    assert first is second

    new_settings = SimpleNamespace(
        webhook_secret="secret-2",
        webhook_signature_tolerance_sec=60,
        webhook_integrations_path=tmp_path / "other.json",
    )
    new_settings.webhook_integrations_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(dependencies, "get_app_settings", lambda: new_settings)
    third = dependencies.get_webhook_service()
    assert third is not first


@pytest.mark.asyncio
async def test_require_active_session_rejects_missing_session():
    class DummyService:
        def get_session(self, session_id):
            return None

        def ensure_csrf_token(self, session_id):
            return "token"

    request = _make_request(method="GET", cookies={"session_id": "abc"})
    with pytest.raises(HTTPException) as exc:
        await dependencies.require_active_session(request, session_service=DummyService())
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_active_session_enforces_csrf_header():
    class DummyService:
        def __init__(self):
            self.session = {"user": "ana"}

        def get_session(self, session_id):
            return dict(self.session)

        def ensure_csrf_token(self, session_id):
            return "expected"

    request = _make_request(
        method="POST",
        headers=[(b"content-type", b"application/json")],
        cookies={"session_id": "active"},
    )
    with pytest.raises(HTTPException) as exc:
        await dependencies.require_active_session(request, session_service=DummyService())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_active_session_accepts_form_token():
    class DummyService:
        def get_session(self, session_id):
            return {"user": "ana"}

        def ensure_csrf_token(self, session_id):
            return "expected"

    body = b"csrf_token=expected"
    body_sent = False

    async def receive():
        nonlocal body_sent
        if body_sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        body_sent = True
        return {"type": "http.request", "body": body, "more_body": False}
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [
            (b"content-type", b"application/x-www-form-urlencoded"),
            (b"cookie", b"session_id=abc"),
        ],
    }
    request = Request(scope, receive)
    session = await dependencies.require_active_session(request, session_service=DummyService())

    assert session["csrf_token"] == "expected"
    assert session["session_id"] == "abc"
