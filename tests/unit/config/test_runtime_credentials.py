import base64
import json
import os

import pytest

from config.runtime_credentials import RuntimeCredentialStore


def _generate_secret() -> str:
    return base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8")


def test_store_encrypts_payload_and_logs_audit(tmp_path, monkeypatch):
    secret = _generate_secret()
    monkeypatch.setenv("CREDENTIALS_SECRET_KEY", secret)
    creds_path = tmp_path / "creds.json"
    audit_path = tmp_path / "audit.log"

    store = RuntimeCredentialStore(path=creds_path, audit_path=audit_path)
    store.update(whisper_api_key="abc123", chatgpt_api_key="xyz987")

    raw = json.loads(creds_path.read_text(encoding="utf-8"))
    assert raw["encrypted"] is True
    assert "payload" in raw

    decoded = store.read()
    assert decoded["whisper"]["api_key"] == "abc123"
    assert decoded["chatgpt"]["api_key"] == "xyz987"

    audit_contents = audit_path.read_text(encoding="utf-8").strip()
    assert audit_contents  # at least one entry logged


def test_encrypted_payload_requires_secret(tmp_path, monkeypatch):
    secret = _generate_secret()
    monkeypatch.setenv("CREDENTIALS_SECRET_KEY", secret)
    creds_path = tmp_path / "creds.json"
    store = RuntimeCredentialStore(path=creds_path)
    store.update(whisper_api_key="secure")

    # Remove secret and ensure store refuses to operate
    monkeypatch.delenv("CREDENTIALS_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError):
        RuntimeCredentialStore(path=creds_path)
