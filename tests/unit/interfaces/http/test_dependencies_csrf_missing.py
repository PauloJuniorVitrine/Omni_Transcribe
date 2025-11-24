from __future__ import annotations

import pytest
from fastapi import HTTPException

from interfaces.http.dependencies import require_active_session, get_session_service, get_app_settings


class _SessionService:
    def __init__(self):
        self.return_session = {"csrf_token": "abc", "metadata": {}}

    def get_session(self, session_id):
        return self.return_session

    def ensure_csrf_token(self, session_id):
        return "abc"


def test_require_active_session_missing_csrf_raises(monkeypatch):
    monkeypatch.setattr("interfaces.http.dependencies.get_session_service", lambda: _SessionService())
    settings = type("S", (), {"test_mode": False})()
    monkeypatch.setattr("interfaces.http.dependencies.get_app_settings", lambda: settings)

    class _Req:
        method = "POST"
        headers = {}
        cookies = {}
        url = type("U", (), {"path": "/protected"})

        async def form(self):
            return {}

    with pytest.raises(HTTPException):
        import asyncio
        asyncio.get_event_loop().run_until_complete(require_active_session(_Req()))
