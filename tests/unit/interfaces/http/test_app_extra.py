import os
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from interfaces.http import app as http_app


class DummySettings(types.SimpleNamespace):
    pass


@pytest.fixture
def dummy_settings(tmp_path, monkeypatch):
    settings = DummySettings(
        app_env="test",
        base_output_dir=tmp_path / "out",
        openai_chunk_trigger_mb=1,
        max_audio_size_mb=5,
        openai_base_url="http://invalid",
        openai_api_key="k",
        chatgpt_api_key="k",
    )
    monkeypatch.setattr(http_app, "get_settings", lambda: settings)
    return settings


def test_health_check_degraded(tmp_path, monkeypatch, dummy_settings):
    monkeypatch.setenv("HEALTH_PROBE_OPENAI", "1")
    monkeypatch.setattr(http_app, "_feature_flags_snapshot", lambda: {"downloads.signature_required": True})
    client = TestClient(http_app.app)
    resp = client.get("/health")
    assert resp.status_code == 206
    data = resp.json()
    assert data["status"] == "degraded"
    assert "external" in data


def test_dashboard_summary_uses_controller(monkeypatch):
    class _Controller:
        def list_jobs(self, limit, page=1):
            return [], False

    http_app.app.dependency_overrides[http_app.get_job_controller_dep] = lambda: _Controller()
    http_app.app.dependency_overrides[http_app.require_active_session] = lambda: {}
    http_app._feature_flags_snapshot = lambda: {}
    client = TestClient(http_app.app)
    resp = client.get("/api/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total"] == 0
    http_app.app.dependency_overrides.clear()


def test_dashboard_incidents(monkeypatch):
    http_app.app.dependency_overrides[http_app.require_active_session] = lambda: {}
    monkeypatch.setattr(http_app, "_get_recent_incidents", lambda limit=5: [{"event": "e"}])
    client = TestClient(http_app.app)
    resp = client.get("/api/dashboard/incidents")
    assert resp.status_code == 200
    assert resp.json()["items"] == [{"event": "e"}]
    http_app.app.dependency_overrides.clear()


def test_api_settings_page_disabled(monkeypatch):
    http_app.app.dependency_overrides[http_app.require_active_session] = lambda: {}
    monkeypatch.setattr(http_app, "_feature_flags_snapshot", lambda: {"ui.api_settings": False})
    client = TestClient(http_app.app)
    resp = client.get("/settings/api")
    assert resp.status_code == 404
    http_app.app.dependency_overrides.clear()
