from __future__ import annotations

import os
import re
import shutil
from urllib.parse import quote
from pathlib import Path

from fastapi.testclient import TestClient

from config import get_settings, reload_settings
from domain.entities.artifact import Artifact
from domain.entities.job import Job
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus
from infrastructure.container import get_container
from infrastructure.container.service_container import ServiceContainer


def test_job_detail_renders_signed_links_and_download(monkeypatch, tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    # Copia assets necessários (templates/static/perfis) para o tmp e muda cwd
    shutil.copytree(repo_root / "src" / "interfaces" / "web" / "templates", tmp_path / "src" / "interfaces" / "web" / "templates")
    shutil.copytree(repo_root / "src" / "interfaces" / "web" / "static", tmp_path / "src" / "interfaces" / "web" / "static")
    shutil.copytree(repo_root / "profiles", tmp_path / "profiles")
    monkeypatch.chdir(tmp_path)
    # Isola ambiente e configura diretórios/base de dados em tmp
    os.environ["TEST_MODE"] = "1"
    os.environ["OPENAI_API_KEY"] = "test-key"
    # Deixa o cofre em modo memória (sem secret) durante o teste
    os.environ.pop("CREDENTIALS_SECRET_KEY", None)
    os.environ["SKIP_RUNTIME_CREDENTIALS_VERIFY"] = "1"
    os.environ["WEBHOOK_SECRET"] = "secret-download"
    os.environ["BASE_OUTPUT_DIR"] = str(tmp_path / "output")
    os.environ["BASE_PROCESSING_DIR"] = str(tmp_path / "processing")
    os.environ["BASE_BACKUP_DIR"] = str(tmp_path / "backup")
    os.environ["BASE_INPUT_DIR"] = str(tmp_path / "inbox")
    os.environ["BASE_REJECTED_DIR"] = str(tmp_path / "rejected")
    # Flag de assinatura ativa
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    feature_flags_path = config_dir / "feature_flags.json"
    feature_flags_path.write_text('{"downloads.signature_required": true}', encoding="utf-8")
    os.environ["CONFIG_DIR"] = str(config_dir)  # compat local, fallback

    reload_settings()
    settings = get_settings()
    settings.ensure_runtime_directories()

    # Recria container com settings isolados
    get_container._instance = ServiceContainer(settings=settings)  # type: ignore[attr-defined]
    container = get_container()

    job_repo = container.job_repository
    artifact_repo = container.artifact_repository

    job_id = "job-signature-1"
    job = Job(
        id=job_id,
        source_path=Path(settings.base_input_dir) / "sample.wav",
        profile_id="geral",
        status=JobStatus.AWAITING_REVIEW,
        engine=EngineType.OPENAI,
    )
    job_repo.create(job)

    # Cria artefato físico
    job_dir = Path(settings.base_output_dir) / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = job_dir / f"{job_id}_v1.txt"
    artifact_path.write_text("conteudo de teste", encoding="utf-8")

    artifact = Artifact(
        id="artifact-1",
        job_id=job_id,
        artifact_type=ArtifactType.TRANSCRIPT_TXT,
        path=artifact_path,
        version=1,
    )
    artifact_repo.save_many([artifact])
    job.attach_artifact(artifact.artifact_type, artifact.path)
    job_repo.update(job)

    # Importa app após ambiente configurado
    from interfaces.http import app as app_mod
    from interfaces.http.dependencies import require_active_session

    app_mod.app.dependency_overrides[require_active_session] = lambda: {}
    client = TestClient(app_mod.app)

    resp = client.get(f"/jobs/{job_id}")
    assert resp.status_code == 200
    html = resp.text
    assert "token=" in html and "expires=" in html

    match = re.search(r"/artifacts\?[^\"']+", html)
    assert match, "Download link não encontrado no HTML"

    # Gera token com a mesma rotina do servidor para evitar divergência de encoding
    token, expires = app_mod._sign_download(str(artifact_path))  # type: ignore[attr-defined]
    encoded_path = quote(str(artifact_path))
    encoded_expires = quote(expires)
    download_url = f"/artifacts?path={encoded_path}&token={token}&expires={encoded_expires}&job_id={job_id}"

    download_resp = client.get(download_url, headers={"accept": "text/plain"})
    assert download_resp.status_code == 200
    assert "conteudo de teste" in download_resp.text
