from __future__ import annotations

import pytest
from types import SimpleNamespace

from infrastructure.container import components_asr


def _base_settings(**overrides):
    defaults = dict(
        asr_engine="openai",
        openai_api_key="test-key",
        openai_whisper_api_key="",
        openai_base_url="https://api.example.com/v1",
        openai_whisper_model="whisper-1",
        chatgpt_api_key="chat-key",
        chatgpt_model="gpt-4o-mini",
        post_edit_model="gpt-4.1",
        local_whisper_model_size="medium",
        openai_chunk_duration_sec=900,
        openai_chunk_trigger_mb=200,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_build_core_usecases_raises_without_api_key():
    settings = _base_settings(openai_api_key="", chatgpt_api_key="")
    with pytest.raises(RuntimeError):
        components_asr._build_asr_clients(settings)  # type: ignore[attr-defined]


def test_build_asr_clients_supports_local_engine(monkeypatch):
    settings = _base_settings(asr_engine="local", openai_api_key="")
    monkeypatch.setattr(components_asr, "FasterWhisperClient", lambda *args, **kwargs: "local-client")
    clients = components_asr._build_asr_clients(settings)  # type: ignore[attr-defined]
    assert "local" in clients
    assert "openai" not in clients


def test_build_core_usecases_wire_services(monkeypatch):
    settings = _base_settings()
    job_repo = SimpleNamespace()
    profile_provider = SimpleNamespace()
    log_repo = SimpleNamespace()
    review_repo = SimpleNamespace()
    sheet_service = SimpleNamespace()
    status_publisher = SimpleNamespace()
    rejected_logger = SimpleNamespace()

    create_job, run_asr, post_edit, retry, handle_review, asr_service, post_edit_service = components_asr.build_core_usecases(
        settings,
        job_repo,
        profile_provider,
        log_repo,
        review_repo,
        sheet_service,
        status_publisher,
        rejected_logger,
    )

    assert create_job is not None
    assert run_asr is not None
    assert post_edit is not None
    assert retry is not None
    assert handle_review is not None
    assert asr_service is not None
    assert post_edit_service is not None
