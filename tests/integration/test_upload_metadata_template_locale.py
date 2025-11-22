from __future__ import annotations

import os
from fastapi.testclient import TestClient
import shutil
from pathlib import Path

from interfaces.http.app import app
from interfaces.http.dependencies import require_active_session
from infrastructure.container import get_container
from domain.entities.value_objects import EngineType
from config import get_settings


def test_upload_sets_template_and_locale(tmp_path, monkeypatch):
    app.dependency_overrides[require_active_session] = lambda: {}
    repo_root = Path(__file__).resolve().parents[2]
    # Copia assets web para o tmp para satisfazer Jinja2
    target_templates = tmp_path / "src" / "interfaces" / "web" / "templates"
    target_static = tmp_path / "src" / "interfaces" / "web" / "static"
    target_templates.mkdir(parents=True, exist_ok=True)
    target_static.mkdir(parents=True, exist_ok=True)
    if (repo_root / "src" / "interfaces" / "web" / "templates").exists():
        shutil.copytree(repo_root / "src" / "interfaces" / "web" / "templates", target_templates, dirs_exist_ok=True)
    if (repo_root / "src" / "interfaces" / "web" / "static").exists():
        shutil.copytree(repo_root / "src" / "interfaces" / "web" / "static", target_static, dirs_exist_ok=True)
    monkeypatch.chdir(tmp_path)
    from config import reload_settings

    os.environ["OPENAI_API_KEY"] = "test-key"
    os.environ["BASE_INPUT_DIR"] = str(tmp_path / "inbox")
    os.environ["BASE_OUTPUT_DIR"] = str(tmp_path / "output")
    os.environ["BASE_PROCESSING_DIR"] = str(tmp_path / "processing")
    os.environ["BASE_BACKUP_DIR"] = str(tmp_path / "backup")
    os.environ["BASE_REJECTED_DIR"] = str(tmp_path / "rejected")
    os.environ["CSV_LOG_PATH"] = str(tmp_path / "output" / "log.csv")
    reload_settings()
    settings = get_settings()
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    # Write profile with delivery_template/default_locale metadata
    (profiles_dir / "geral.prompt.txt").write_text(
        """---
id: geral
delivery_template: custom
default_locale: pt-BR
---
Prompt""",
        encoding="utf-8",
    )
    # minimal template required for artifact builder wiring
    templates_dir = profiles_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    (templates_dir / "custom.template.txt").write_text("---\nid: custom\n---\n{{transcript}}", encoding="utf-8")
    settings.ensure_runtime_directories()

    from infrastructure.container.service_container import ServiceContainer

    get_container._instance = ServiceContainer(settings=settings)  # type: ignore[attr-defined]
    # garante que registry de templates recarregue novos arquivos
    from interfaces.http import app as app_mod
    app_mod._app_settings = settings  # type: ignore[attr-defined]
    app_mod._templates_dir = Path(settings.profiles_dir) / "templates"  # type: ignore[attr-defined]
    app_mod._template_audit_path = app_mod._templates_dir / "templates_audit.log"  # type: ignore[attr-defined]
    app_mod._reload_template_registry()  # type: ignore[attr-defined]
    # confirma que template custom está carregado ou cai para default sem quebrar
    registry = app_mod._get_template_registry()  # type: ignore[attr-defined]
    registry.get("custom")

    client = TestClient(app)
    audio = tmp_path / "inbox" / "geral" / "audio.wav"
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"RIFF0000")
    files = {"file": ("audio.wav", audio.read_bytes(), "audio/wav")}
    data = {"profile": "geral", "engine": EngineType.OPENAI.value, "auto_process": "false"}

    resp = client.post("/jobs/upload", files=files, data=data, headers={"accept": "application/json"})
    assert resp.status_code in (200, 303, 307)

    job = get_container().job_repository.list_recent(1)[0]
    assert job.metadata.get("delivery_template") == "custom"
    assert job.metadata.get("delivery_locale") == "pt-br"
    app.dependency_overrides.clear()
