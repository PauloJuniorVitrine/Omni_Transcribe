from __future__ import annotations

import json
import secrets
import time
from pathlib import Path
from typing import Any, Dict, Optional

from filelock import FileLock


class SessionService:
    """Persists OAuth sessions on disk to protect the review UI."""

    def __init__(self, storage_path: Path, ttl_minutes: int = 720) -> None:
        self.storage_path = storage_path
        self.ttl_minutes = ttl_minutes
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(str(self.storage_path) + ".lock")
        if not self.storage_path.exists():
            self.storage_path.write_text("{}", encoding="utf-8")

    @property
    def ttl_seconds(self) -> int:
        return int(self.ttl_minutes * 60)

    def create_session(self, tokens: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """Store token payload and return opaque session id."""
        session_id = secrets.token_urlsafe(32)
        payload = {
            "tokens": tokens,
            "metadata": metadata or {},
            "created_at": time.time(),
        }
        with self.lock:
            data = self._read_store()
            data[session_id] = payload
            data = self._remove_expired(data)
            self._write_store(data)
        return session_id

    def get_session(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        with self.lock:
            data = self._read_store()
            record = data.get(session_id)
            if not record:
                return None
            if self._is_expired(record.get("created_at", 0.0)):
                del data[session_id]
                self._write_store(data)
                return None
            return record

    def invalidate_session(self, session_id: str) -> None:
        with self.lock:
            data = self._read_store()
            if session_id in data:
                del data[session_id]
                self._write_store(data)

    def ensure_csrf_token(self, session_id: str) -> str:
        token = secrets.token_urlsafe(32)
        with self.lock:
            data = self._read_store()
            record = data.get(session_id)
            if not record:
                return token
            metadata = record.setdefault("metadata", {})
            existing = metadata.get("csrf_token")
            if existing:
                return existing
            metadata["csrf_token"] = token
            data[session_id] = record
            self._write_store(data)
            return token

    # Internals
    def _read_store(self) -> Dict[str, Dict[str, Any]]:
        try:
            return json.loads(self.storage_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write_store(self, data: Dict[str, Dict[str, Any]]) -> None:
        self.storage_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _remove_expired(self, data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        keys_to_delete = [key for key, value in data.items() if self._is_expired(value.get("created_at", 0.0))]
        for key in keys_to_delete:
            del data[key]
        return data

    def _is_expired(self, created_at: float) -> bool:
        return (time.time() - created_at) > self.ttl_seconds


__all__ = ["SessionService"]
