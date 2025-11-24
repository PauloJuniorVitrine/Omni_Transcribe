from __future__ import annotations

import pytest

from config import Settings
from infrastructure.container import components_asr, components_delivery, components_storage


def test_components_asr_requires_openai_key(monkeypatch) -> None:
    settings = Settings()
    settings.openai_api_key = ""
    settings.asr_engine = "openai"
    with pytest.raises(RuntimeError):
        components_asr._build_asr_clients(settings)


def test_components_delivery_missing_sheet_id_raises(monkeypatch) -> None:
    settings = Settings()
    settings.google_sheets_enabled = True
    settings.google_sheets_spreadsheet_id = ""
    with pytest.raises(RuntimeError):
        components_delivery._build_sheet_gateway(settings)


def test_components_storage_sqlite_backend(tmp_path) -> None:
    settings = Settings()
    settings.persistence_backend = "sqlite"
    settings.database_url = f"sqlite:///{tmp_path/'db.sqlite'}"
    job_repo, artifact_repo, log_repo, review_repo, profile_provider = components_storage.build_repositories(
        tmp_path, settings
    )
    assert job_repo is not None and artifact_repo is not None and log_repo is not None and review_repo is not None
