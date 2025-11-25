from __future__ import annotations

from config.settings import Settings
from infrastructure.container import components_asr


def test_build_asr_clients_requires_openai():
    settings = Settings()
    settings.openai_api_key = ""
    settings.openai_whisper_api_key = ""
    settings.asr_engine = "openai"
    try:
        components_asr._build_asr_clients(settings)
    except RuntimeError as exc:
        assert "OPENAI_API_KEY" in str(exc)


def test_build_asr_clients_includes_openai():
    settings = Settings()
    settings.openai_api_key = "sk-test"
    settings.asr_engine = "openai"
    clients = components_asr._build_asr_clients(settings)
    assert "openai" in clients
