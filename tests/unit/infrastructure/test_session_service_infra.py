from __future__ import annotations

import time
from pathlib import Path

from application.services.session_service import SessionService


def test_session_creation_and_expiry(tmp_path):
    storage = tmp_path / "sessions.json"
    service = SessionService(storage_path=storage, ttl_minutes=0.02)
    session_id = service.create_session({"token": "abc"})
    assert isinstance(session_id, str)
    recovered = service.get_session(session_id)
    assert recovered is not None
    time.sleep(1.1)
    expired = service.get_session(session_id)
    assert expired is None


def test_csrf_token_persistence(tmp_path):
    service = SessionService(storage_path=tmp_path / "sessions.json")
    sid = service.create_session({"token": "abc"})
    token = service.ensure_csrf_token(sid)
    assert token
    same = service.ensure_csrf_token(sid)
    assert token == same


def test_invalidate_session(tmp_path):
    service = SessionService(storage_path=tmp_path / "sessions.json")
    sid = service.create_session({"token": "abc"})
    assert service.get_session(sid)
    service.invalidate_session(sid)
    assert service.get_session(sid) is None
