from __future__ import annotations

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import config
from interfaces.http import app as http_app
from interfaces.http.app import app
from interfaces.http.dependencies import require_active_session
from application.services.delivery_template_service import DeliveryTemplate
from tests.integration.test_http_api import StubJobController, StubJobRepository


def test_find_assets_root_prefers_meipass(monkeypatch, tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    target = bundle / "interfaces" / "web"
    target.mkdir(parents=True)

    monkeypatch.setattr(http_app.sys, "_MEIPASS", str(bundle), raising=False)
    try:
        resolved = http_app._find_assets_root()
        assert resolved == target
    finally:
        if hasattr(http_app.sys, "_MEIPASS"):
            monkeypatch.delattr(http_app.sys, "_MEIPASS", raising=False)


def test_branding_logo_url_returns_timestamp(monkeypatch, tmp_path: Path) -> None:
    branding = tmp_path / "branding"
    branding.mkdir(parents=True)
    (branding / "logo.png").write_bytes(b"logo")

    monkeypatch.setattr(http_app, "_BRANDING_DIR", branding)
    url = http_app._branding_logo_url()

    assert url is not None
    assert url.startswith("/branding/logo")
    assert "ts=" in url


def test_branding_logo_url_returns_none_when_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(http_app, "_BRANDING_DIR", tmp_path / "missing-branding")
    assert http_app._branding_logo_url() is None


def test_find_assets_root_returns_default_when_no_candidates(monkeypatch) -> None:
    monkeypatch.setattr(http_app.Path, "exists", lambda self: False)
    result = http_app._find_assets_root()

    assert result == Path("src/interfaces/web")


def _reload_app_with_env(monkeypatch, env_vars: dict[str, str]):
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    config.reload_settings()
    try:
        importlib.reload(http_app)
    finally:
        for key in env_vars:
            monkeypatch.delenv(key, raising=False)
        config.reload_settings()
        importlib.reload(http_app)


def test_reload_raises_when_webhook_secrets_not_set(monkeypatch):
    env = {
        "APP_ENV": "production",
        "WEBHOOK_SECRET": "changeme",
        "DOWNLOAD_TOKEN_SECRET": "",
        "CORS_ALLOWED_ORIGINS": '["https://example.com"]',
    }
    with pytest.raises(RuntimeError):
        _reload_app_with_env(monkeypatch, env)


def test_reload_raises_when_cors_wildcard_in_production(monkeypatch):
    env = {
        "APP_ENV": "production",
        "WEBHOOK_SECRET": "strong",
        "DOWNLOAD_TOKEN_SECRET": "strong",
        "CORS_ALLOWED_ORIGINS": '["*"]',
    }
    with pytest.raises(RuntimeError):
        _reload_app_with_env(monkeypatch, env)


def test_get_branding_logo_missing(monkeypatch):
    monkeypatch.setattr(http_app, "_BRANDING_DIR", Path("missing-dir"))
    client = TestClient(app)
    response = client.get("/branding/logo")
    assert response.status_code == 404


def test_upload_branding_logo_invalid_extension(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(http_app, "_BRANDING_DIR", tmp_path / "branding")
    app.dependency_overrides[require_active_session] = lambda: {"user": "test"}
    client = TestClient(app)
    response = client.post(
        "/settings/branding/logo",
        files={"logo": ("logo.txt", b"data", "text/plain")},
    )
    assert response.status_code == 400
    assert "Formato de logo" in response.json()["detail"]


def test_upload_branding_logo_empty(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(http_app, "_BRANDING_DIR", tmp_path / "branding")
    app.dependency_overrides[require_active_session] = lambda: {"user": "test"}
    client = TestClient(app)
    response = client.post(
        "/settings/branding/logo",
        files={"logo": ("logo.png", b"", "image/png")},
    )
    assert response.status_code == 400
    assert "Arquivo vazio" in response.json()["detail"]


def test_upload_branding_logo_success(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(http_app, "_BRANDING_DIR", tmp_path / "branding")
    app.dependency_overrides[require_active_session] = lambda: {"user": "test"}
    client = TestClient(app)
    response = client.post(
        "/settings/branding/logo",
        files={"logo": ("logo.png", b"data", "image/png")},
        headers={"accept": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_production_headers_on_root(monkeypatch):
    env = {
        "APP_ENV": "production",
        "WEBHOOK_SECRET": "strong",
        "DOWNLOAD_TOKEN_SECRET": "strong",
        "CORS_ALLOWED_ORIGINS": '["https://example.com"]',
    }
    _reload_app_with_env(monkeypatch, env)
    client = TestClient(app)
    response = client.get("/")
    assert response.headers.get("Strict-Transport-Security")


def _setup_job_detail(monkeypatch):
    job = Job(
        id="job-detail",
        source_path=Path("inbox/none"),
        profile_id="geral",
        engine=EngineType.OPENAI,
        status=JobStatus.PENDING,
        metadata={
            "delivery_template": "missing-template",
            "delivery_template_updated_at": "2025-01-01T00:00:00Z",
        },
    )
    repo = StubJobRepository(job)
    controller = StubJobController(repo)
    app.dependency_overrides[get_job_controller_dep] = lambda: controller
    app.dependency_overrides[require_active_session] = lambda: {"user": "test"}
    return job, controller


def test_job_detail_missing(monkeypatch):
    job, controller = _setup_job_detail(monkeypatch)
    controller.job_repository.jobs = []
    client = TestClient(app)
    response = client.get(f"/jobs/{job.id}")
    assert response.status_code == 404


def test_job_detail_template_fallback(monkeypatch, tmp_path: Path):
    job, controller = _setup_job_detail(monkeypatch)

    class StubTemplateRegistry:
        default_template_id = "default"

        def list_templates(self):
            return [
                DeliveryTemplate(
                    id="default",
                    name="Default",
                    description="Default desc",
                    body="{{}}",
                    source_path=tmp_path / "default.template.txt",
                )
            ]

        def get(self, template_id: str):
            raise FileNotFoundError

    monkeypatch.setattr(http_app, "_get_template_registry", lambda: StubTemplateRegistry())
    client = TestClient(app)
    response = client.get(f"/jobs/{job.id}")
    assert response.status_code == 200
