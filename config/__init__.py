"""Global configuration helpers for TranscribeFlow."""

from functools import lru_cache
from typing import Dict, Any

from .runtime_credentials import RuntimeCredentialStore, DEFAULT_CREDENTIALS
from .settings import Settings
from .feature_flags import FeatureFlagProvider

_runtime_store = RuntimeCredentialStore()
_feature_flags = FeatureFlagProvider()


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance (loads from environment/.env)."""
    settings = Settings()
    credentials = _runtime_store.read()
    _apply_runtime_overrides(settings, credentials)
    return settings


def reload_settings() -> None:
    """Clear cache so next call reloads env/runtime overrides."""
    cache_clear = getattr(get_settings, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()


def get_runtime_store() -> RuntimeCredentialStore:
    return _runtime_store


def get_feature_flags() -> FeatureFlagProvider:
    return _feature_flags


def _apply_runtime_overrides(settings: Settings, credentials: Dict[str, Dict[str, str]]) -> None:
    whisper = {**DEFAULT_CREDENTIALS["whisper"], **credentials.get("whisper", {})}
    chatgpt = {**DEFAULT_CREDENTIALS["chatgpt"], **credentials.get("chatgpt", {})}

    whisper_key = whisper.get("api_key") or settings.openai_whisper_api_key or settings.openai_api_key
    if whisper_key:
        settings.openai_whisper_api_key = whisper_key
        settings.openai_api_key = whisper_key
    settings.openai_whisper_model = whisper.get("model") or settings.openai_whisper_model

    chat_key = chatgpt.get("api_key") or settings.chatgpt_api_key or settings.openai_api_key
    if chat_key:
        settings.chatgpt_api_key = chat_key
        settings.openai_api_key = chat_key
    chat_model = chatgpt.get("model") or settings.chatgpt_model or settings.post_edit_model
    settings.chatgpt_model = chat_model
    settings.post_edit_model = chat_model


__all__ = ["Settings", "get_settings", "reload_settings", "get_runtime_store"]
