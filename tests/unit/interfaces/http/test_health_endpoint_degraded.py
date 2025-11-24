from __future__ import annotations

from fastapi.testclient import TestClient

import interfaces.http.app as http_app
from interfaces.http.app import app


def test_health_endpoint_handles_missing_app_env(monkeypatch):
    fake_settings = type(
        "Settings",
        (),
        {
            "app_env": "test",
            "openai_api_key": "",
            "chatgpt_api_key": "",
            "base_output_dir": "output",
            "openai_chunk_trigger_mb": 0,
            "max_audio_size_mb": 1,
        },
    )()
    monkeypatch.setattr(http_app, "get_settings", lambda: fake_settings)

    client = TestClient(app)
    resp = client.get("/health")

    assert resp.status_code in (200, 206)
    assert "status" in resp.json()
