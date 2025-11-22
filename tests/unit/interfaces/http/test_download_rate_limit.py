from __future__ import annotations

import time

import pytest
from fastapi import HTTPException

from interfaces.http.app import _enforce_download_rate


def test_enforce_download_rate_allows_within_limit():
    # single call should not raise
    _enforce_download_rate("session-1")


def test_enforce_download_rate_blocks_after_limit(monkeypatch):
    # shrink window/limit for deterministic behavior
    monkeypatch.setattr("interfaces.http.app._DOWNLOAD_RATE_LIMIT", 2, raising=False)
    monkeypatch.setattr("interfaces.http.app._DOWNLOAD_RATE_WINDOW_SEC", 60, raising=False)

    _enforce_download_rate("sess-x")
    _enforce_download_rate("sess-x")
    with pytest.raises(HTTPException):
        _enforce_download_rate("sess-x")

    # other session unaffected
    _enforce_download_rate("sess-y")
