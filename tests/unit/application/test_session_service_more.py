from __future__ import annotations

import json
from pathlib import Path

from application.services.session_service import SessionService


def test_get_session_expires_and_removes(tmp_path: Path, monkeypatch) -> None:
    store = tmp_path / "store.json"
    service = SessionService(store, ttl_minutes=0)
    session_id = service.create_session(tokens={"t": 1})

    monkeypatch.setattr("application.services.session_service.time.time", lambda: 9999999.0)
    assert service.get_session(session_id) is None
    # expired session removed from store
    assert json.loads(store.read_text()) == {}


def test_write_store_persists_json(tmp_path: Path) -> None:
    service = SessionService(tmp_path / "store.json", ttl_minutes=1)
    data = {"a": {"tokens": {"x": 1}}}
    service._write_store(data)
    assert json.loads((tmp_path / "store.json").read_text(encoding="utf-8"))["a"]["tokens"]["x"] == 1
