from __future__ import annotations

import time
from pathlib import Path

from application.services.session_service import SessionService


def _make_service(tmp_path: Path, ttl_minutes: int = 60) -> SessionService:
    storage = tmp_path / "sessions" / "sessions.json"
    return SessionService(storage_path=storage, ttl_minutes=ttl_minutes)


def test_session_lifecycle_create_get_invalidate(tmp_path):
    service = _make_service(tmp_path)
    session_id = service.create_session(tokens={"access": "abc"}, metadata={"user": "ana"})

    stored = service.get_session(session_id)
    assert stored is not None
    assert stored["tokens"]["access"] == "abc"
    assert stored["metadata"]["user"] == "ana"

    service.invalidate_session(session_id)
    assert service.get_session(session_id) is None


def test_session_expiration_removes_record(tmp_path):
    service = _make_service(tmp_path, ttl_minutes=0)
    session_id = service.create_session(tokens={}, metadata=None)

    # force expiry by waiting a tiny amount (ttl=0 -> immediate)
    time.sleep(0.01)
    assert service.get_session(session_id) is None

    # ensure expired entry removed from storage
    with service.lock:
        data = service._read_store()  # type: ignore[attr-defined]
    assert session_id not in data


def test_ensure_csrf_token_persists(tmp_path):
    service = _make_service(tmp_path)
    session_id = service.create_session(tokens={}, metadata=None)

    token_a = service.ensure_csrf_token(session_id)
    assert token_a

    # Calling again should return same value without creating duplicates.
    token_b = service.ensure_csrf_token(session_id)
    assert token_a == token_b

    # Removing metadata entry should regenerate a different token.
    with service.lock:
        data = service._read_store()  # type: ignore[attr-defined]
        entry = data[session_id]
        entry["metadata"].pop("csrf_token", None)
        service._write_store(data)  # type: ignore[attr-defined]

    token_c = service.ensure_csrf_token(session_id)
    assert token_c and token_c != token_a
