from __future__ import annotations

import json
from pathlib import Path

from application.services.session_service import SessionService


def test_get_session_returns_none_for_missing(tmp_path: Path) -> None:
    service = SessionService(tmp_path / "store.json", ttl_minutes=1)
    assert service.get_session(None) is None


def test_expired_session_is_removed(monkeypatch, tmp_path: Path) -> None:
    now = 1_000_000.0

    def _time():
        return now

    monkeypatch.setattr("application.services.session_service.time.time", _time)
    service = SessionService(tmp_path / "store.json", ttl_minutes=0)  # expires immediately

    session_id = service.create_session(tokens={"t": 1})
    now += 5  # advance time past ttl
    assert service.get_session(session_id) is None


def test_ensure_csrf_token_reuses_existing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("application.services.session_service.time.time", lambda: 10.0)
    service = SessionService(tmp_path / "store.json", ttl_minutes=1)
    session_id = service.create_session(tokens={"a": 1})

    first = service.ensure_csrf_token(session_id)
    again = service.ensure_csrf_token(session_id)

    assert first == again
    record = service.get_session(session_id)
    assert record and record["metadata"]["csrf_token"] == first


def test_read_store_handles_corrupted_json(tmp_path: Path) -> None:
    store = tmp_path / "store.json"
    store.write_text("{invalid", encoding="utf-8")
    service = SessionService(store, ttl_minutes=1)
    assert service._read_store() == {}
