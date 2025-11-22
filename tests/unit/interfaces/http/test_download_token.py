from __future__ import annotations

import hmac
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest
from fastapi import HTTPException

from interfaces.http.app import _validate_download_token
from config import get_settings


def _make_token(path: str, expires_iso: str) -> str:
    secret = get_settings().webhook_secret.encode("utf-8")
    payload = f"{path}:{expires_iso}".encode("utf-8")
    return hmac.new(secret, payload, sha256).hexdigest()


def test_validate_download_token_accepts_valid_signature():
    path = "output/job/file.txt"
    expires = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    token = _make_token(path, expires)

    _validate_download_token(path=path, token=token, expires=expires)


@pytest.mark.parametrize(
    "token,expires,reason",
    [
        (None, None, "missing token"),
        ("bad", None, "missing expires"),
    ],
)
def test_validate_download_token_rejects_missing(token, expires, reason):
    path = "output/job/file.txt"
    with pytest.raises(HTTPException):
        _validate_download_token(path=path, token=token, expires=expires)


def test_validate_download_token_rejects_expired_or_invalid():
    path = "output/job/file.txt"
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    valid_future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    bad_token = "x" * 64

    with pytest.raises(HTTPException):
        _validate_download_token(path=path, token=_make_token(path, expired), expires=expired)
    with pytest.raises(HTTPException):
        _validate_download_token(path=path, token=bad_token, expires=valid_future)
