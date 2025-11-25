from __future__ import annotations

import hashlib
import hmac
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import interfaces.http.app as http_app


def test_sanitize_upload_filename_valid_and_invalid():
    assert http_app._sanitize_upload_filename("Meu Audio.WAV") == "Meu-Audio.wav"
    assert http_app._sanitize_upload_filename("audio-longo.MP3") == "audio-longo.mp3"
    with pytest.raises(HTTPException):
        http_app._sanitize_upload_filename("../fora.wav")
    with pytest.raises(HTTPException):
        http_app._sanitize_upload_filename("sem-extensao")


def test_validate_upload_mime_rejects_invalid():
    http_app._validate_upload_mime("audio/wav")
    http_app._validate_upload_mime("audio/mp3; charset=utf-8")
    with pytest.raises(HTTPException):
        http_app._validate_upload_mime("text/plain")


def test_sign_download_matches_expected_hmac(monkeypatch):
    settings = SimpleNamespace(webhook_secret="secret-key", download_token_secret="")
    monkeypatch.setattr(http_app, "get_settings", lambda: settings)

    path = "/output/arquivo.txt"
    signature, expires = http_app._sign_download(path, ttl_minutes=1)
    payload = f"{path}:{expires}".encode("utf-8")
    expected = hmac.new(settings.webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    assert signature == expected


def test_feature_flags_snapshot_returns_dict():
    result = http_app._feature_flags_snapshot()
    assert isinstance(result, dict)


def test_health_endpoint_reports_external(tmp_path, monkeypatch):
    settings = SimpleNamespace(
        app_env="test",
        openai_api_key="test",
        chatgpt_api_key="test",
        openai_chunk_trigger_mb=10,
        max_audio_size_mb=2048,
        max_request_body_mb=512,
        base_output_dir=tmp_path / "output",
        openai_base_url="https://example.com",
    )
    settings.base_output_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(http_app, "get_settings", lambda: settings)
    monkeypatch.setattr(http_app, "get_feature_flags", lambda: SimpleNamespace(snapshot=lambda: {"downloads.signature_required": True}))

    client = TestClient(http_app.app)
    response = client.get("/health")
    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] in {"ok", "degraded"}
    assert payload["external"]["asr_ready"] is True
    assert payload["external"]["chat_ready"] is True
