from __future__ import annotations

from pathlib import Path
import os
from typing import Dict, Tuple

from fastapi import Depends, HTTPException, Request

import config
from config import Settings

from application.services.session_service import SessionService
from application.services.webhook_service import WebhookService


def get_app_settings() -> Settings:
    """Return current Settings instance (patched-friendly)."""
    return config.get_settings()


_webhook_service_cache: Dict[Tuple[str, int, str], WebhookService] = {}
_session_service_cache: Dict[Tuple[str, int], SessionService] = {}


def get_webhook_service() -> WebhookService:
    """Provide WebhookService wired with current settings."""
    settings = get_app_settings()
    cache_key = (
        settings.webhook_secret,
        settings.webhook_signature_tolerance_sec,
        str(settings.webhook_integrations_path),
    )
    service = _webhook_service_cache.get(cache_key)
    if not service:
        service = WebhookService(settings=settings)
        _webhook_service_cache[cache_key] = service
    return service


def get_session_service() -> SessionService:
    """Return persistent session service bound to processing directory."""
    settings = get_app_settings()
    storage_path = Path(settings.base_processing_dir) / "sessions" / "sessions.json"
    cache_key = (str(storage_path), settings.session_ttl_minutes)
    service = _session_service_cache.get(cache_key)
    if not service:
        service = SessionService(storage_path=storage_path, ttl_minutes=settings.session_ttl_minutes)
        _session_service_cache[cache_key] = service
    return service


async def require_active_session(
    request: Request,
    session_service: SessionService = Depends(get_session_service),
) -> Dict[str, str]:
    settings = get_app_settings()
    if not hasattr(session_service, "get_session"):
        session_service = get_session_service()
    test_mode = os.getenv("TEST_MODE") == "1" or os.getenv("OMNI_TEST_MODE") == "1" or getattr(settings, "test_mode", False)
    if test_mode and getattr(settings, "app_env", "development") != "production":
        # Bypass auth entirely in test/dev mode so the bundled app abre sem OAuth.
        return {"user": "test", "session_id": "test", "csrf_token": "test", "metadata": {"display_name": "Local"}}

    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="Sessao inativa.")
    session = session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=401, detail="Sessao expirada ou invalida.")
    if session_id:
        session["session_id"] = session_id
        csrf_token = session_service.ensure_csrf_token(session_id)
        session["csrf_token"] = csrf_token
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            token = request.headers.get("X-CSRF-Token")
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
                form = await request.form()
                form_token = form.get("csrf_token")
                if form_token:
                    token = form_token
            if not token or token != csrf_token:
                raise HTTPException(status_code=403, detail="CSRF token invalido.")
    return session


__all__ = [
    "get_app_settings",
    "get_webhook_service",
    "get_session_service",
    "require_active_session",
]
