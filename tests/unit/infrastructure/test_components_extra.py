import pytest
from types import SimpleNamespace
from pathlib import Path

from infrastructure.container import components_storage, components_delivery, components_asr


class _Settings(SimpleNamespace):
    pass


def test_build_repositories_sqlite_branch(tmp_path):
    settings = _Settings(
        persistence_backend="sqlite",
        database_url=f"sqlite:///{tmp_path/'db.sqlite'}",
        profiles_dir=tmp_path,
    )
    job_repo, artifact_repo, log_repo, review_repo, profile_provider = components_storage.build_repositories(
        tmp_path, settings
    )
    assert job_repo.__class__.__name__.startswith("Sql")
    assert artifact_repo.__class__.__name__.startswith("Sql")
    assert log_repo.__class__.__name__.startswith("Sql")
    assert review_repo.__class__.__name__.startswith("Sql")
    assert profile_provider is not None


def test_build_sheet_gateway_raises_without_spreadsheet_id():
    settings = _Settings(
        google_sheets_enabled=True,
        google_sheets_spreadsheet_id="",
        google_sheets_credentials_path="c",
        google_sheets_worksheet="w",
    )
    with pytest.raises(RuntimeError):
        components_delivery._build_sheet_gateway(settings)


def test_build_asr_clients_errors_without_openai_key():
    settings = _Settings(
        openai_whisper_api_key=None,
        openai_api_key=None,
        openai_base_url="http://localhost",
        openai_whisper_model="whisper-1",
        asr_engine="openai",
    )
    with pytest.raises(RuntimeError):
        components_asr._build_asr_clients(settings)


def test_build_chat_client_requires_api_key():
    settings = _Settings(openai_api_key=None, chatgpt_api_key=None, openai_base_url="http://", chatgpt_model="gpt")
    with pytest.raises(RuntimeError):
        components_asr._build_chat_client(settings)
