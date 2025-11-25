from __future__ import annotations

import csv
import hashlib
import hmac
import io
import json
import logging
import re
import unicodedata
import urllib.parse
import os
import sys
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import deque
import time
from typing import Any, Deque, Dict, List, Optional, TypedDict
import requests

from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from application.controllers.job_controller import JobController
from application.controllers.review_controller import ReviewController
from application.services.job_log_service import JobLogService
from application.services.delivery_template_service import DeliveryTemplateRegistry
from config import get_settings, get_runtime_store, reload_settings, get_feature_flags, profile_loader
import yaml
from domain.entities.job import Job
from domain.entities.log_entry import LogEntry
from domain.entities.value_objects import ArtifactType, EngineType, JobStatus, LogLevel
from infrastructure.container import get_container
from infrastructure.telemetry.metrics_logger import record_metric, notify_alert, load_entries, summarize_metrics
from . import auth_routes, webhook_routes
from .dependencies import require_active_session
from .schemas import (
    DashboardSummaryResponse,
    DashboardIncidentsResponse,
    JobsFeedResponse,
    JobLogsResponse,
    ProcessJobResponse,
    TemplateRawResponse,
    TemplatePreviewResponse,
    UpdateTemplateResponse,
    UpdateLocaleResponse,
    UploadJobResponse,
    UploadTokenResponse,
)

app = FastAPI(title="TranscribeFlow")
logger = logging.getLogger("transcribeflow.http")
def _find_assets_root() -> Path:
    """Resolve assets path both in source tree and in PyInstaller bundle."""
    candidates = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "interfaces" / "web")
        candidates.append(Path(meipass) / "src" / "interfaces" / "web")
    here = Path(__file__).resolve()
    try:
        # src/interfaces/http -> parents[2] == src
        candidates.append(here.parents[2] / "interfaces" / "web")
        candidates.append(here.parents[3] / "src" / "interfaces" / "web")
    except IndexError:
        pass
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path("src/interfaces/web")


_ASSETS_ROOT = _find_assets_root()
templates = Jinja2Templates(directory=str(_ASSETS_ROOT / "templates"))
app.mount("/static", StaticFiles(directory=str(_ASSETS_ROOT / "static")), name="static")
app.include_router(auth_routes.router)
app.include_router(webhook_routes.router)

_app_settings = get_settings()
_runtime_store = get_runtime_store()
_feature_flags = get_feature_flags()
if _app_settings.app_env == "production":
    weak_secrets = {None, "", "changeme"}
    if (_app_settings.webhook_secret in weak_secrets) and (getattr(_app_settings, "download_token_secret", "") in weak_secrets):
        raise RuntimeError("WEBHOOK_SECRET ou DOWNLOAD_TOKEN_SECRET precisam ser definidos em producao.")
_ROOT_DIR = Path(__file__).resolve().parents[3]
_profiles_dir = Path(_app_settings.profiles_dir)
if not _profiles_dir.is_absolute():
    _profiles_dir = (_ROOT_DIR / _profiles_dir).resolve()
_templates_dir = _profiles_dir / "templates"
_templates_dir.mkdir(parents=True, exist_ok=True)
_template_audit_path = _templates_dir / "templates_audit.log"
_template_registry = DeliveryTemplateRegistry(_templates_dir)
_TEMPLATE_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_LOCALE_PATTERN = re.compile(r"^[a-z]{2}(?:[-_][a-z0-9]+)?$", re.IGNORECASE)
_BRANDING_DIR = Path(_app_settings.base_processing_dir) / "branding"
_ALLOWED_LOGO_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}

_DOWNLOAD_RATE_WINDOW_SEC = 60
_DOWNLOAD_RATE_LIMIT = 30
_download_tracker: Dict[str, Deque[float]] = {}
_API_RATE_WINDOW_SEC = 60
_API_RATE_LIMIT = 60
_api_rate_tracker: Dict[str, Deque[float]] = {}
UPLOAD_TOKEN_TTL_MINUTES = 10

# Fail-fast: em produção não aceitamos CORS wildcard
if _app_settings.app_env == "production" and "*" in (_app_settings.cors_allowed_origins or []):
    raise RuntimeError("CORS_ALLOWED_ORIGINS não pode conter '*' em produção.")

# CORS middleware (configurável via settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(_app_settings, "cors_allowed_origins", ["*"]),
    allow_credentials=getattr(_app_settings, "cors_allow_credentials", False),
    allow_methods=getattr(_app_settings, "cors_allowed_methods", ["*"]),
    allow_headers=getattr(_app_settings, "cors_allowed_headers", ["*"]),
)


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    trace_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers.setdefault("X-Request-ID", trace_id)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if getattr(_app_settings, "app_env", "development") == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
    return response


def _reload_template_registry() -> None:
    global _template_registry
    _template_registry = DeliveryTemplateRegistry(_templates_dir)


def _get_template_registry() -> DeliveryTemplateRegistry:
    return _template_registry
def _get_trace_id(request: Request) -> str:
    return getattr(request.state, "trace_id", "")

def _branding_logo_url() -> Optional[str]:
    if not _BRANDING_DIR.exists():
        return None
    for ext in (".png", ".jpg", ".jpeg", ".webp", ".svg"):
        candidate = _BRANDING_DIR / f"logo{ext}"
        if candidate.exists():
            ts = int(candidate.stat().st_mtime)
            return f"/branding/logo?ts={ts}"
    return None

# Artifact download whitelist & signature
ALLOWED_DOWNLOAD_EXTENSIONS = {"txt", "srt", "vtt", "json", "zip"}
ALLOWED_UPLOAD_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
ALLOWED_UPLOAD_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/aac",
    "audio/flac",
    "audio/ogg",
    "audio/mp4",
    "audio/x-m4a",
}
ARTIFACT_TOKEN_TTL_MINUTES = 10


def _sanitize_upload_filename(filename: str) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="Arquivo invalido.")
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Arquivo invalido.")
    base = Path(filename).name
    extension = Path(base).suffix.lower()
    if extension not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Extensao de audio nao permitida.")
    stem = Path(base).stem
    normalized = unicodedata.normalize("NFKD", stem)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", ascii_only).strip("._-")
    safe_stem = cleaned or "upload"
    safe_name = f"{safe_stem[:80]}{extension}"
    if ".." in safe_name or "/" in safe_name or "\\" in safe_name:
        raise HTTPException(status_code=400, detail="Arquivo invalido.")
    return safe_name


def _validate_upload_mime(content_type: Optional[str]) -> None:
    if not content_type:
        return
    normalized = content_type.split(";")[0].strip().lower()
    if normalized and normalized not in ALLOWED_UPLOAD_MIME_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de arquivo nao permitido.")


async def _persist_upload_file(file: UploadFile, profile: str, max_bytes: int) -> tuple[Path, int]:
    sanitized_name = _sanitize_upload_filename(file.filename or "")
    _validate_upload_mime(file.content_type)
    suffix = Path(sanitized_name).suffix.lower()
    target_dir = Path(get_settings().base_input_dir) / (profile or "geral")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / sanitized_name
    if target.exists():
        target = target_dir / f"{Path(sanitized_name).stem}_{int(time.time())}{suffix}"
    total_read = 0
    chunk_size = max(1024 * 1024, min(4 * 1024 * 1024, max_bytes // 4 or max_bytes))
    try:
        with target.open("wb") as dest:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total_read += len(chunk)
                if total_read > max_bytes:
                    dest.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(status_code=400, detail="Arquivo excede limite configurado.")
                dest.write(chunk)
    finally:
        await file.close()
    return target, total_read


def _sign_download(path: str, ttl_minutes: int = ARTIFACT_TOKEN_TTL_MINUTES) -> tuple[str, str]:
    """
    Constrói token HMAC + expiração para links de download de artefatos.
    Usa o mesmo segredo aplicado na validação para evitar divergências.
    """
    settings = get_settings()
    secret_value = getattr(settings, "download_token_secret", "") or settings.webhook_secret
    secret = secret_value.encode("utf-8")
    expires_dt = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    expires = expires_dt.isoformat()
    signature_payload = f"{path}:{expires}".encode("utf-8")
    token = hmac.new(secret, signature_payload, hashlib.sha256).hexdigest()
    return token, expires

class FlashPayload(TypedDict):
    text: str
    variant: str


_FLASH_MESSAGES: Dict[str, FlashPayload] = {
    "review-approved": {"text": "Revisao registrada como aprovada.", "variant": "success"},
    "review-adjust": {"text": "Revisao marcada como precisando de ajustes.", "variant": "warning"},
    "download-error": {"text": "Nao foi possivel baixar o arquivo solicitado.", "variant": "error"},
    "login-success": {"text": "Sessao iniciada com sucesso.", "variant": "success"},
    "process-started": {"text": "Processamento assincrono iniciado para este job.", "variant": "info"},
    "process-error": {"text": "Falha ao iniciar o processamento. Verifique os logs.", "variant": "error"},
    "upload-success": {"text": "Upload recebido e job criado.", "variant": "success"},
    "flags-updated": {"text": "Feature flags atualizadas.", "variant": "success"},
    "api-settings-saved": {"text": "Credenciais atualizadas com sucesso.", "variant": "success"},
    "template-updated": {"text": "Formato de entrega atualizado.", "variant": "success"},
    "template-created": {"text": "Template criado com sucesso.", "variant": "success"},
}
_LEVEL_ICONS = {
    LogLevel.INFO: "[i]",
    LogLevel.WARNING: "[!]",
    LogLevel.ERROR: "[x]",
}
_LEVEL_ICON_MAP = {level.value: icon for level, icon in _LEVEL_ICONS.items()}

AVAILABLE_WHISPER_MODELS = [
    "gpt-4o-mini-transcribe",
    "gpt-4o-transcribe",
    "whisper-1",
]

AVAILABLE_CHATGPT_MODELS = [
    "gpt-4.1-mini",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4o",
]


@app.middleware("http")
async def enforce_request_size(request: Request, call_next):
    max_bytes = _app_settings.max_request_body_mb * 1024 * 1024
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > max_bytes:
        return JSONResponse(status_code=413, content={"detail": "Payload excede limite configurado."})
    response = await call_next(request)
    return response


def get_job_controller_dep() -> JobController:
    container = get_container()
    return JobController(
        job_repository=container.job_repository,
        create_job_use_case=container.create_job_use_case,
        pipeline_use_case=container.pipeline_use_case,
        retry_use_case=container.retry_use_case,
    )


def get_review_controller_dep() -> ReviewController:
    container = get_container()
    return ReviewController(
        job_repository=container.job_repository,
        handle_review_use_case=container.handle_review_use_case,
        sheet_service=container.sheet_service,
        register_delivery_use_case=container.register_delivery_use_case,
    )


def get_job_log_service() -> JobLogService:
    container = get_container()
    return JobLogService(container.log_repository)


def _feature_flags_snapshot() -> Dict[str, bool]:
    provider = get_feature_flags()
    return provider.snapshot()


@app.get("/", response_class=HTMLResponse)
async def list_jobs(
    request: Request,
    job_controller: JobController = Depends(get_job_controller_dep),
    limit: int = 20,
    page: int = 1,
    status: Optional[str] = None,
    profile: Optional[str] = None,
    accuracy: Optional[str] = None,
    session: dict | None = Depends(require_active_session),
) -> HTMLResponse:
    limit = max(1, min(limit, 200))
    page = max(page, 1)
    jobs, has_more = job_controller.list_jobs(limit, page)
    page_generated_at = datetime.now(timezone.utc)
    page_generated_label = page_generated_at.strftime("%d/%m/%Y %H:%M:%S")
    filtered_jobs = _apply_filters(jobs, status=status, profile=profile, accuracy=accuracy)
    summary = _compute_summary(jobs)
    accuracy_summary = _compute_accuracy_summary(jobs)
    template_registry = _get_template_registry()
    template_options = [
        {
            "id": template.id,
            "name": template.name,
            "description": template.description or "Sem descricao.",
        }
        for template in template_registry.list_templates()
    ]
    template_preview = template_registry.render(None, _build_preview_context())
    template_default_id = template_registry.default_template_id
    profile_options = sorted({job.profile_id for job in jobs})
    flash = _get_flash_message(request.query_params.get("flash"))
    incidents = _get_recent_incidents(limit=5)
    session_info = _summarize_session(session)
    feature_flags = _feature_flags_snapshot()
    context = {
        "jobs": filtered_jobs,
        "summary": summary,
        "selected_status": status or "",
        "selected_profile": profile or "",
        "selected_accuracy": accuracy or "",
        "page": page,
        "limit": limit,
        "has_more": has_more,
        "next_page": page + 1 if has_more else None,
        "prev_page": page - 1 if page > 1 else None,
        "profile_options": profile_options,
        "engine_options": [engine.value for engine in EngineType],
        "status_options": [job_status.value for job_status in JobStatus],
        "accuracy_options": ["passing", "needs_review"],
        "flash_message": flash,
        "incidents": incidents,
        "level_icons": _LEVEL_ICON_MAP,
        "header_session": session_info,
        "page_generated_label": page_generated_label,
        "feature_flags": feature_flags,
        "csrf_token": (session or {}).get("csrf_token", ""),
        "accuracy_summary": accuracy_summary,
        "max_audio_size_mb": getattr(_app_settings, "max_audio_size_mb", 0),
        "health_status": _health_snapshot(),
        "branding_logo_url": _branding_logo_url(),
        "template_preview": template_preview,
        "template_preview_default": template_default_id,
        "template_options": template_options,
    }
    return templates.TemplateResponse(request, "jobs.html", context)


@app.get("/health", response_class=JSONResponse)
async def healthcheck() -> JSONResponse:
    """
    Health endpoint com sinais básicos e probes externos opcionais.
    """
    settings = get_settings()
    assets_ok = Path("src/interfaces/web/static").exists() and Path("src/interfaces/web/templates").exists()
    external = {}
    # Probes leves: evitam levantar exceção; apenas anotam estado
    try:
        external["asr_ready"] = bool(settings.openai_api_key)
    except Exception:
        external["asr_ready"] = False
    try:
        external["chat_ready"] = bool(settings.chatgpt_api_key or settings.openai_api_key)
    except Exception:
        external["chat_ready"] = False
    try:
        # Storage dir writeable
        probe_path = Path(settings.base_output_dir) / ".health_probe"
        probe_path.parent.mkdir(parents=True, exist_ok=True)
        probe_path.write_text("ok", encoding="utf-8")
        probe_path.unlink(missing_ok=True)
        external["storage_ready"] = True
    except Exception:
        external["storage_ready"] = False

    payload = {
        "status": "ok",
        "env": settings.app_env,
        "chunking_mb": settings.openai_chunk_trigger_mb,
        "max_audio_mb": settings.max_audio_size_mb,
        "downloads_signature": _feature_flags_snapshot().get("downloads.signature_required", True),
        "static_assets": assets_ok,
        "external": external,
    }
    degraded = False
    probe_openai = os.getenv("HEALTH_PROBE_OPENAI") == "1"
    if probe_openai:
        external["openai_probe"] = _probe_http(settings.openai_base_url or "", timeout_sec=2)
        degraded = degraded or not external["openai_probe"]
    degraded = degraded or not all(external.values())
    payload["status"] = "degraded" if degraded else "ok"
    return JSONResponse(payload, status_code=200 if not degraded else 206)


@app.get("/api/dashboard/summary", response_class=JSONResponse, response_model=DashboardSummaryResponse)
async def api_dashboard_summary(
    job_controller: JobController = Depends(get_job_controller_dep),
    limit: int = 100,
    _: dict | None = Depends(require_active_session),
) -> JSONResponse:
    _enforce_api_rate("summary")
    limit = max(1, min(limit, 200))
    jobs, _ = job_controller.list_jobs(limit, page=1)
    summary = _compute_summary(jobs)
    accuracy_summary = _compute_accuracy_summary(jobs)
    payload = {
        "summary": summary,
        "accuracy": accuracy_summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    record_metric(
        "dashboard.summary.requested",
        {"total": summary["total"], "awaiting_review": summary["awaiting_review"], "limit": limit},
    )
    return JSONResponse(payload)


@app.get("/api/dashboard/incidents", response_class=JSONResponse, response_model=DashboardIncidentsResponse)
async def api_dashboard_incidents(
    limit: int = 5,
    _: dict | None = Depends(require_active_session),
) -> JSONResponse:
    _enforce_api_rate("incidents")
    incidents = _get_recent_incidents(limit=limit)
    payload = {
        "items": incidents,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    record_metric("dashboard.incidents.requested", {"count": len(incidents), "limit": limit})
    return JSONResponse(payload)


@app.get("/api/dashboard/jobs", response_class=JSONResponse, response_model=JobsFeedResponse)
async def api_dashboard_jobs(
    status: Optional[str] = None,
    profile: Optional[str] = None,
    accuracy: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    _: dict | None = Depends(require_active_session),
) -> JSONResponse:
    _enforce_api_rate("jobs")
    limit = max(1, min(limit, 200))
    page = max(page, 1)
    window = limit * page + limit
    container = get_container()
    jobs = container.job_repository.list_recent(window)
    filtered = _apply_filters(jobs, status=status, profile=profile, accuracy=accuracy)
    start = (page - 1) * limit
    page_items = filtered[start : start + limit]
    has_more = len(filtered) > start + limit
    payload = {
        "jobs": [_serialize_job_for_feed(job) for job in page_items],
        "summary": _compute_summary(filtered),
        "accuracy": _compute_accuracy_summary(filtered),
        "page": page,
        "limit": limit,
        "has_more": has_more,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    record_metric("dashboard.jobs.requested", {"limit": limit, "page": page, "status": status or "", "profile": profile or ""})
    return JSONResponse(payload)


@app.get("/settings/api", response_class=HTMLResponse)
async def api_settings_page(
    request: Request,
    session: dict | None = Depends(require_active_session),
) -> HTMLResponse:
    feature_flags = _feature_flags_snapshot()
    if not feature_flags.get("ui.api_settings", True):
        raise HTTPException(status_code=404, detail="Configuracao indisponivel.")
    flash = _get_flash_message(request.query_params.get("flash"))
    credentials = _runtime_store.read()
    whisper = credentials.get("whisper", {})
    chatgpt = credentials.get("chatgpt", {})
    context = {
        "flash_message": flash,
        "header_session": _summarize_session(session),
        "whisper": {
            "api_key": whisper.get("api_key", ""),
            "model": whisper.get("model", AVAILABLE_WHISPER_MODELS[0]),
        },
        "chatgpt": {
            "api_key": chatgpt.get("api_key", ""),
            "model": chatgpt.get("model", AVAILABLE_CHATGPT_MODELS[0]),
        },
        "whisper_models": AVAILABLE_WHISPER_MODELS,
        "chatgpt_models": AVAILABLE_CHATGPT_MODELS,
        "feature_flags": feature_flags,
        "csrf_token": (session or {}).get("csrf_token", ""),
        "branding_logo_url": _branding_logo_url(),
    }
    return templates.TemplateResponse(request, "api_settings.html", context)


@app.post("/settings/api")
async def api_settings_update(
    request: Request,
    target: str = Form(...),
    whisper_api_key: str = Form(""),
    whisper_model: str = Form(""),
    chatgpt_api_key: str = Form(""),
    chatgpt_model: str = Form(""),
    _: dict | None = Depends(require_active_session),
) -> Response:
    if whisper_model not in AVAILABLE_WHISPER_MODELS:
        whisper_model = AVAILABLE_WHISPER_MODELS[0]
    if chatgpt_model not in AVAILABLE_CHATGPT_MODELS:
        chatgpt_model = AVAILABLE_CHATGPT_MODELS[0]
    if target == "whisper":
        _runtime_store.update(whisper_api_key=whisper_api_key, whisper_model=whisper_model)
    elif target == "chatgpt":
        _runtime_store.update(chatgpt_api_key=chatgpt_api_key, chatgpt_model=chatgpt_model)
    else:
        _runtime_store.update(
            whisper_api_key=whisper_api_key,
            whisper_model=whisper_model,
            chatgpt_api_key=chatgpt_api_key,
            chatgpt_model=chatgpt_model,
        )
    reload_settings()
    flash_token = "api-settings-saved"
    accept = (request.headers.get("accept") or "").lower()
    if "application/json" in accept:
        now_iso = datetime.now(timezone.utc).isoformat()
        now_human = datetime.now(timezone.utc).strftime("%H:%M:%S")
        payload = {
            "status": "ok",
            "flash": flash_token,
            "message": _FLASH_MESSAGES[flash_token]["text"],
            "updated_at": now_iso,
            "updated_at_human": now_human,
            "target": target,
        }
        return JSONResponse(payload)
    return RedirectResponse("/settings/api?flash=api-settings-saved", status_code=303)


@app.get("/settings/templates", response_class=HTMLResponse)
async def template_settings_page(
    request: Request,
    session: dict | None = Depends(require_active_session),
) -> HTMLResponse:
    flash = _get_flash_message(request.query_params.get("flash"))
    registry = _get_template_registry()
    template_rows = [
        {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "path": str(template.source_path),
        }
        for template in registry.list_templates()
    ]
    context = {
        "request": request,
        "flash_message": flash,
        "header_session": _summarize_session(session),
        "templates": template_rows,
        "template_audit": _load_template_audit(),
        "csrf_token": (session or {}).get("csrf_token", ""),
        "branding_logo_url": _branding_logo_url(),
    }
    return templates.TemplateResponse(request, "template_settings.html", context)


@app.get("/settings/flags", response_class=HTMLResponse)
async def flag_settings_page(
    request: Request,
    session: dict | None = Depends(require_active_session),
) -> HTMLResponse:
    flash = _get_flash_message(request.query_params.get("flash"))
    flags = _feature_flags_snapshot()
    rows = [{"name": name, "enabled": value} for name, value in sorted(flags.items())]
    context = {
        "request": request,
        "flash_message": flash,
        "header_session": _summarize_session(session),
        "flags": rows,
        "csrf_token": (session or {}).get("csrf_token", ""),
        "branding_logo_url": _branding_logo_url(),
    }
    return templates.TemplateResponse(request, "flag_settings.html", context)


@app.post("/settings/flags")
async def update_flag(request: Request, _: dict | None = Depends(require_active_session)) -> Response:
    form = await request.form()
    provider = get_feature_flags()
    for key, value in form.items():
        if not key.startswith("flag_"):
            continue
        name = key.replace("flag_", "", 1)
        provider.set_flag(name, value == "on")
    return RedirectResponse("/settings/flags?flash=flags-updated", status_code=303)


@app.post("/settings/templates")
async def create_template_definition(
    request: Request,
    template_id: str = Form(...),
    name: str = Form(""),
    description: str = Form(""),
    body: str = Form(...),
    locale: str = Form(""),
    _: dict | None = Depends(require_active_session),
) -> Response:
    slug = _normalize_template_id(template_id)
    body_value = body.strip()
    if not body_value:
        raise HTTPException(status_code=400, detail="Corpo do template no pode estar vazio.")
    resolved_name = name.strip() or slug.replace("-", " ").title()
    resolved_description = description.strip()
    _templates_dir.mkdir(parents=True, exist_ok=True)
    target = _templates_dir / f"{slug}.template.txt"
    if target.exists():
        raise HTTPException(status_code=400, detail="J existe template com este identificador.")
    locale_code = _normalize_locale_code(locale)
    content = _compose_template_file(
        template_id=slug,
        name=resolved_name,
        description=resolved_description,
        body=body_value,
        locale=locale_code,
    )
    target.write_text(content, encoding="utf-8")
    _reload_template_registry()
    _append_template_audit(
        action="create",
        template_id=slug,
        metadata={"name": resolved_name, "description": resolved_description},
    )
    payload = {
        "status": "ok",
        "template": {"id": slug, "name": resolved_name, "description": resolved_description},
        "message": _FLASH_MESSAGES["template-created"]["text"],
    }
    accept = (request.headers.get("accept") or "").lower()
    if "application/json" in accept:
        return JSONResponse(payload)
    return RedirectResponse("/settings/templates?flash=template-created", status_code=303)


@app.post("/settings/templates/{template_id}/update")
async def update_template_definition(
    request: Request,
    template_id: str,
    name: str = Form(""),
    description: str = Form(""),
    body: str = Form(...),
    locale: str = Form(""),
    _: dict | None = Depends(require_active_session),
) -> Response:
    slug = _normalize_template_id(template_id)
    target = _templates_dir / f"{slug}.template.txt"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Template no encontrado.")
    body_value = body.strip()
    if not body_value:
        raise HTTPException(status_code=400, detail="Corpo do template no pode estar vazio.")
    registry = _get_template_registry()
    existing = registry.get(slug)
    resolved_name = name.strip() or existing.name
    resolved_description = description.strip() or existing.description
    locale_code = _normalize_locale_code(locale) or existing.locale
    content = _compose_template_file(
        template_id=slug,
        name=resolved_name,
        description=resolved_description,
        body=body_value,
        locale=locale_code,
    )
    target.write_text(content, encoding="utf-8")
    _reload_template_registry()
    _append_template_audit(
        action="update",
        template_id=slug,
        metadata={"name": resolved_name, "description": resolved_description},
    )
    payload = {
        "status": "ok",
        "template": {"id": slug, "name": resolved_name, "description": resolved_description},
        "message": "Template atualizado com sucesso.",
    }
    accept = (request.headers.get("accept") or "").lower()
    if "application/json" in accept:
        return JSONResponse(payload)
    return RedirectResponse("/settings/templates?flash=template-updated", status_code=303)


@app.get("/settings/templates/{template_id}/raw", response_model=TemplateRawResponse)
async def get_template_raw(
    template_id: str,
    _: dict | None = Depends(require_active_session),
) -> JSONResponse:
    slug = _normalize_template_id(template_id)
    target = _templates_dir / f"{slug}.template.txt"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Template no encontrado.")
    content = target.read_text(encoding="utf-8")
    segments = content.split("---")
    body = segments[2].strip() if len(segments) >= 3 else content
    template = _get_template_registry().get(slug)
    return JSONResponse(
        {
            "id": slug,
            "name": template.name,
            "description": template.description,
            "body": body,
            "locale": template.locale,
        }
    )


@app.post("/settings/templates/preview", response_model=TemplatePreviewResponse)
async def preview_template_body(
    body: str = Form(...),
    _: dict | None = Depends(require_active_session),
) -> JSONResponse:
    rendered = _render_template_body(body, _build_preview_context())
    return JSONResponse({"rendered": rendered})


@app.get("/api/templates/preview", response_model=TemplatePreviewResponse)
async def api_templates_preview(
    template_id: Optional[str] = None,
    _: dict | None = Depends(require_active_session),
) -> JSONResponse:
    rendered = _get_template_registry().render(template_id, _build_preview_context())
    return JSONResponse({"rendered": rendered})


@app.delete("/settings/templates/{template_id}")
async def delete_template_definition(
    template_id: str,
    _: dict | None = Depends(require_active_session),
) -> JSONResponse:
    slug = _normalize_template_id(template_id)
    target = _templates_dir / f"{slug}.template.txt"
    if not target.exists():
        raise HTTPException(status_code=404, detail="Template no encontrado.")
    if slug == _get_template_registry().default_template_id:
        raise HTTPException(status_code=400, detail="Template padro no pode ser removido.")
    target.unlink()
    _reload_template_registry()
    _append_template_audit(action="delete", template_id=slug, metadata={})
    return JSONResponse({"status": "ok", "template": slug})


@app.get("/ui/theme-preview", response_class=HTMLResponse)
async def theme_preview(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "theme_preview.html",
        {
            "header_session": None,
            "branding_logo_url": _branding_logo_url(),
        },
    )


@app.post("/api/jobs/{job_id}/process", response_model=ProcessJobResponse)
async def api_process_job(
    job_id: str,
    job_controller: JobController = Depends(get_job_controller_dep),
    _: dict | None = Depends(require_active_session),
) -> JSONResponse:
    try:
        job_controller.process_job(job_id)
    except Exception as exc:
        logger.error("Falha ao processar job via API", exc_info=True, extra={"job_id": job_id})
        raise HTTPException(status_code=400, detail=str(exc))
    logger.info("Processamento solicitado via API", extra={"job_id": job_id})
    return JSONResponse({"job_id": job_id, "status": "processing"})


@app.post("/jobs/upload")
async def upload_job(
    request: Request,
    file: UploadFile = File(...),
    profile: str = Form("geral"),
    engine: str = Form("openai"),
    auto_process: bool = Form(False),
    job_controller: JobController = Depends(get_job_controller_dep),
    _: dict | None = Depends(require_active_session),
) -> Response:
    settings = get_settings()
    max_bytes = settings.max_audio_size_mb * 1024 * 1024
    target, total_read = await _persist_upload_file(file, profile, max_bytes)

    if total_read == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    try:
        engine_value = EngineType(engine)
    except Exception:
        engine_value = EngineType.OPENAI
    job = job_controller.ingest_file(target, profile, engine_value)
    flash_token = "upload-success"
    if auto_process:
        try:
            job_controller.process_job(job.id)
            flash_token = "process-started"
        except Exception:
            flash_token = "process-error"
    return RedirectResponse(url=f"/jobs/{job.id}?flash={flash_token}", status_code=303)


@app.get("/api/uploads/token", response_model=UploadTokenResponse)
async def api_upload_token(
    profile: str = "geral",
    engine: str = "openai",
    ttl_minutes: int = 10,
    _: dict | None = Depends(require_active_session),
) -> JSONResponse:
    ttl = max(1, min(ttl_minutes, 60))
    engine_value = engine if engine in {engine_type.value for engine_type in EngineType} else EngineType.OPENAI.value
    token, expires = _sign_upload_token(profile=profile, engine=engine_value, ttl_minutes=ttl)
    payload = {
        "token": token,
        "expires": expires,
        "profile": profile or "geral",
        "engine": engine_value,
        "expires_in_minutes": ttl,
    }
    return JSONResponse(payload)


@app.post("/api/uploads", response_model=UploadJobResponse)
async def api_upload_job(
    file: UploadFile = File(...),
    token: str = Form(...),
    expires: str = Form(...),
    profile: str = Form("geral"),
    engine: str = Form("openai"),
    auto_process: bool = Form(False),
    job_controller: JobController = Depends(get_job_controller_dep),
    _: dict | None = Depends(require_active_session),
) -> JSONResponse:
    _validate_upload_token(token, expires, profile or "geral", engine or EngineType.OPENAI.value)
    settings = get_settings()
    max_bytes = settings.max_audio_size_mb * 1024 * 1024
    target, total_read = await _persist_upload_file(file, profile, max_bytes)
    if total_read == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    try:
        engine_value = EngineType(engine)
    except ValueError:
        engine_value = EngineType.OPENAI
    job = job_controller.ingest_file(target, profile or "geral", engine_value)
    auto_processed = False
    if auto_process:
        try:
            job_controller.process_job(job.id)
            auto_processed = True
        except Exception as exc:
            logger.error("Falha ao iniciar pipeline via API", exc_info=True, extra={"job_id": job.id})
            raise HTTPException(status_code=400, detail=str(exc))
    return JSONResponse(
        {
            "job_id": job.id,
            "status": job.status.value,
            "profile_id": job.profile_id,
            "auto_processed": auto_processed,
        }
    )


@app.post("/jobs/{job_id}/process")
async def ui_process_job(
    job_id: str,
    job_controller: JobController = Depends(get_job_controller_dep),
    _: dict | None = Depends(require_active_session),
) -> RedirectResponse:
    try:
        job_controller.process_job(job_id)
    except Exception:
        logger.error("Falha ao processar job via UI", exc_info=True, extra={"job_id": job_id})
        flash = "process-error"
    else:
        flash = "process-started"
    return RedirectResponse(url=f"/jobs/{job_id}?flash={flash}", status_code=303)


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail(
    job_id: str,
    request: Request,
    job_controller: JobController = Depends(get_job_controller_dep),
    session: dict | None = Depends(require_active_session),
) -> HTMLResponse:
    job = job_controller.job_repository.find_by_id(job_id)  # type: ignore[attr-defined]
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    artifacts = _serialize_artifacts(job.output_paths, job.id)

    transcript_preview = ""
    transcript_path = job.output_paths.get(ArtifactType.TRANSCRIPT_TXT)
    if transcript_path and Path(transcript_path).exists():
        transcript_preview = Path(transcript_path).read_text(encoding="utf-8")
    page_generated_at = datetime.now(timezone.utc)
    page_generated_label = page_generated_at.strftime("%d/%m/%Y %H:%M:%S")
    flash_message = _get_flash_message(request.query_params.get("flash"))
    feature_flags = _feature_flags_snapshot()
    profile_template_id: Optional[str] = None
    try:
        profile_doc = profile_loader.load_profile(job.profile_id, _profiles_dir)
        profile_template_id = (profile_doc.meta or {}).get("delivery_template")
    except Exception:
        profile_template_id = None
    selected_template_id = job.metadata.get("delivery_template") or profile_template_id
    template_options: List[Dict[str, str]] = []
    selected_template_description = ""
    template_registry = _get_template_registry()
    if template_registry:
        if not selected_template_id:
            selected_template_id = template_registry.default_template_id
        for template in template_registry.list_templates():
            if template.id == selected_template_id:
                selected_template_description = template.description
            template_options.append(
                {
                    "id": template.id,
                    "name": template.name,
                    "description": template.description,
                    "locale": template.locale,
                }
            )
        if selected_template_id and not selected_template_description:
            try:
                selected_template_description = template_registry.get(selected_template_id).description
            except FileNotFoundError:
                selected_template_description = ""
    template_updated_label = _format_template_label(job.metadata.get("delivery_template_updated_at"))
    available_locales = _available_template_locales()
    selected_locale = job.metadata.get("delivery_locale") or _guess_locale(job.language)
    locale_updated_label = _format_template_label(job.metadata.get("delivery_locale_updated_at"))
    accuracy_snapshot = _compose_accuracy_snapshot(job)
    context = {
        "request": request,
        "job": job,
        "artifacts": artifacts,
        "transcript_preview": transcript_preview,
        "log_levels": [level.value for level in LogLevel],
        "level_icons": _LEVEL_ICON_MAP,
        "flash_message": flash_message,
        "header_session": _summarize_session(session),
        "page_generated_label": page_generated_label,
        "feature_flags": feature_flags,
        "delivery_templates": template_options,
        "selected_delivery_template": selected_template_id,
        "selected_template_description": selected_template_description,
        "template_updated_label": template_updated_label,
        "available_locales": available_locales,
        "selected_locale": selected_locale,
        "locale_updated_label": locale_updated_label,
        "accuracy_snapshot": accuracy_snapshot,
        "csrf_token": (session or {}).get("csrf_token", ""),
        "branding_logo_url": _branding_logo_url(),
    }
    return templates.TemplateResponse(request, "job_detail.html", context)


@app.post("/jobs/{job_id}/template", response_model=UpdateTemplateResponse)
async def update_job_template(
    job_id: str,
    request: Request,
    template_id: str = Form(...),
    job_controller: JobController = Depends(get_job_controller_dep),
    _: dict | None = Depends(require_active_session),
) -> Response:
    job = job_controller.job_repository.find_by_id(job_id)  # type: ignore[attr-defined]
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    template_registry = _get_template_registry()
    if not template_registry:
        raise HTTPException(status_code=500, detail="Nenhum template configurado.")
    template = template_registry.get(template_id)
    job.metadata = job.metadata or {}
    timestamp = datetime.now(timezone.utc)
    job.metadata["delivery_template"] = template.id
    job.metadata["delivery_template_updated_at"] = timestamp.isoformat()
    job_controller.job_repository.update(job)
    payload = {
        "status": "ok",
        "template": {
            "id": template.id,
            "name": template.name,
            "description": template.description,
        },
        "updated_at": timestamp.isoformat(),
        "updated_at_human": timestamp.strftime("%H:%M:%S"),
        "message": _FLASH_MESSAGES["template-updated"]["text"],
    }
    accept = (request.headers.get("accept") or "").lower()
    if "application/json" in accept:
        return JSONResponse(payload)
    return RedirectResponse(url=f"/jobs/{job_id}?flash=template-updated", status_code=303)


@app.post("/jobs/{job_id}/locale", response_model=UpdateLocaleResponse)
async def update_job_locale(
    job_id: str,
    request: Request,
    delivery_locale: str = Form(""),
    job_controller: JobController = Depends(get_job_controller_dep),
    _: dict | None = Depends(require_active_session),
) -> Response:
    job = job_controller.job_repository.find_by_id(job_id)  # type: ignore[attr-defined]
    if not job:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    locale = _normalize_locale_code(delivery_locale) or None
    job.metadata = job.metadata or {}
    timestamp = datetime.now(timezone.utc)
    if locale:
        job.metadata["delivery_locale"] = locale
        job.metadata["delivery_locale_updated_at"] = timestamp.isoformat()
    else:
        job.metadata.pop("delivery_locale", None)
        job.metadata["delivery_locale_updated_at"] = timestamp.isoformat()
    job_controller.job_repository.update(job)
    payload = {
        "status": "ok",
        "locale": locale,
        "updated_at": timestamp.isoformat(),
        "updated_at_human": timestamp.strftime("%H:%M:%S"),
        "message": "Idioma atualizado.",
    }
    accept = (request.headers.get("accept") or "").lower()
    if "application/json" in accept:
        return JSONResponse(payload)
    return RedirectResponse(url=f"/jobs/{job_id}?flash=template-updated", status_code=303)


@app.get("/api/jobs/{job_id}/logs", response_class=JSONResponse, response_model=JobLogsResponse)
async def api_job_logs(
    job_id: str,
    request: Request,
    job_controller: JobController = Depends(get_job_controller_dep),
    log_service: JobLogService = Depends(get_job_log_service),
    _: dict | None = Depends(require_active_session),
) -> JSONResponse:
    _enforce_api_rate(f"logs:{job_id}")
    job = job_controller.job_repository.find_by_id(job_id)  # type: ignore[attr-defined]
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    level = request.query_params.get("level") or ""
    event_contains = request.query_params.get("event") or ""
    include_all = request.query_params.get("all") == "true"
    page = _safe_int(request.query_params.get("page"), default=1)
    page_size = _safe_int(request.query_params.get("page_size"), default=20, maximum=200)
    query = log_service.query(
        job_id=job_id,
        level=level,
        event_contains=event_contains,
        page=page,
        page_size=page_size,
        include_all=include_all,
    )
    payload = {
        "job_id": job_id,
        "filters": {"level": level, "event": event_contains, "all": include_all},
        "page": query.page,
        "page_size": query.page_size,
        "total": query.total,
        "has_more": query.has_more,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "logs": [JobLogService.serialize(entry) for entry in query.logs],
    }
    return JSONResponse(payload)


@app.get("/api/jobs/{job_id}/logs/export")
async def api_job_logs_export(
    job_id: str,
    format: str = "json",
    level: str = "",
    event: str = "",
    job_controller: JobController = Depends(get_job_controller_dep),
    log_service: JobLogService = Depends(get_job_log_service),
    _: dict | None = Depends(require_active_session),
) -> Response:
    _enforce_api_rate(f"logs_export:{job_id}")
    job = job_controller.job_repository.find_by_id(job_id)  # type: ignore[attr-defined]
    if not job:
        raise HTTPException(status_code=404, detail="Job nao encontrado")
    export_format = format.lower()
    if export_format not in {"csv", "json"}:
        raise HTTPException(status_code=400, detail="Formato invalido; use csv ou json.")
    query = log_service.query(
        job_id=job_id,
        level=level or "",
        event_contains=event or "",
        page=1,
        page_size=50,
        include_all=True,
    )
    return _export_logs(job_id, query.logs, export_format)


@app.get("/api/telemetry/metrics", response_class=JSONResponse)
async def api_telemetry_metrics(
    _: dict | None = Depends(require_active_session),
) -> JSONResponse:
    entries = load_entries(limit=200)
    summary = summarize_metrics()
    payload = {
        "summary": summary,
        "entries": entries,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(payload)


@app.post("/jobs/{job_id}/review")
async def review_job(
    job_id: str,
    reviewer: str = Form(...),
    decision: str = Form(...),
    notes: str = Form(""),
    review_controller: ReviewController = Depends(get_review_controller_dep),
    _: dict | None = Depends(require_active_session),
) -> RedirectResponse:
    approved = decision == "approve"
    review_controller.submit_review(job_id, reviewer=reviewer, approved=approved, notes=notes or None)
    logger.info("Revisao registrada", extra={"job_id": job_id, "approved": approved})
    flash = "review-approved" if approved else "review-adjust"
    return RedirectResponse(url=f"/jobs/{job_id}?flash={flash}", status_code=303)


@app.get("/artifacts", response_model=None)
async def download_artifact(
    request: Request,
    path: str,
    job_id: Optional[str] = None,
    token: Optional[str] = None,
    expires: Optional[str] = None,
    session: dict | None = Depends(require_active_session),
) -> Response:
    file_path = Path(path).resolve()
    accept_html = _wants_html(request)
    session_id = (session or {}).get("session_id")
    client_ip = request.client.host if request and request.client else None
    try:
        settings = get_settings()
        allowed_roots = [Path(settings.base_output_dir).resolve(), Path(settings.base_backup_dir).resolve()]
        if not any(file_path == root or root in file_path.parents for root in allowed_roots):
            raise HTTPException(status_code=400, detail="Caminho invalido.")
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado.")
        suffix = file_path.suffix.lower().lstrip(".")
        if suffix not in settings.allowed_download_extensions:
            raise HTTPException(status_code=400, detail="Extensao nao permitida.")
        rate_key = f"{session_id or 'anonymous'}:{client_ip or 'unknown'}"
        _enforce_download_rate(rate_key)
        if _feature_flags_snapshot().get("downloads.signature_required", True):
            _validate_download_token(path=path, token=token, expires=expires)
    except HTTPException as exc:
        logger.warning(
            "Download redirecionado por erro",
            extra={"job_id": job_id, "path": str(file_path), "detail": exc.detail, "trace_id": _get_trace_id(request)},
        )
        notify_alert(
            "artifact.download.blocked",
            {"job_id": job_id, "path": str(file_path), "detail": exc.detail, "trace_id": _get_trace_id(request)},
        )
        if accept_html:
            target = f"/jobs/{job_id}?flash=download-error" if job_id else "/?flash=download-error"
            return RedirectResponse(url=target, status_code=303)
        raise exc

    logger.info("Download solicitado", extra={"path": str(file_path), "trace_id": _get_trace_id(request)})
    record_metric(
        "artifact.download.success",
        {"job_id": job_id, "path": str(file_path), "extension": file_path.suffix.lower()},
    )
    return FileResponse(file_path)


def _serialize_artifacts(artifacts, job_id: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Retorna metadados de artefatos já com URL assinada para download seguro.
    Codifica query params para evitar falhas de token por caracteres especiais.
    """
    serialized: List[Dict[str, str]] = []
    for artifact_type, path in artifacts.items():
        path_str = str(path)
        token, expires = _sign_download(path_str)
        encoded_path = urllib.parse.quote(path_str)
        encoded_expires = urllib.parse.quote(expires)
        url = f"/artifacts?path={encoded_path}&token={token}&expires={encoded_expires}"
        if job_id:
            url += f"&job_id={job_id}"
        label = artifact_type.value if isinstance(artifact_type, ArtifactType) else str(artifact_type)
        serialized.append(
            {
                "type": label,
                "path": path_str,
                "url": url,
                "extension": Path(path_str).suffix.lower().lstrip("."),
            }
        )
    return serialized


def _serialize_artifacts_dict(artifacts) -> Dict[str, str]:
    """
    Compat helper: retorna dict simples para testes legados que esperam map artifact_type -> path.
    """
    serialized: Dict[str, str] = {}
    for artifact_type, path in artifacts.items():
        if isinstance(artifact_type, ArtifactType):
            serialized[artifact_type.value] = str(path)
        else:
            serialized[str(artifact_type)] = str(path)
    return serialized


def _serialize_job_for_feed(job: Job) -> Dict[str, Any]:
    metadata = job.metadata or {}

    def _as_float(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    requires_review = str(metadata.get("accuracy_requires_review", "")).lower() == "true"
    return {
        "id": job.id,
        "source_name": job.source_path.name if job.source_path else "",
        "profile_id": job.profile_id,
        "status": job.status.value,
        "language": job.language or "",
        "accuracy_status": metadata.get("accuracy_status"),
        "accuracy_score": _as_float(metadata.get("accuracy_score")),
        "accuracy_wer": _as_float(metadata.get("accuracy_wer")),
        "accuracy_requires_review": requires_review,
        "updated_at": job.updated_at.isoformat(),
    }


def _validate_download_token(path: str, token: Optional[str], expires: Optional[str]) -> None:
    settings = get_settings()
    secret_value = getattr(settings, "download_token_secret", "") or settings.webhook_secret
    secret = secret_value.encode("utf-8")
    if not token or not expires:
        raise HTTPException(status_code=401, detail="Token ausente para download.")
    try:
        exp = datetime.fromisoformat(expires)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token invalido.")
    if exp < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Token expirado.")
    signature_payload = f"{path}:{expires}".encode("utf-8")
    expected = hmac.new(secret, signature_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, token):
        raise HTTPException(status_code=401, detail="Token invalido.")


def _get_flash_message(token: Optional[str]) -> Optional[FlashPayload]:
    if not token:
        return None
    return _FLASH_MESSAGES.get(token)


def _sign_upload_token(
    profile: str = "geral",
    engine: str = EngineType.OPENAI.value,
    ttl_minutes: int = UPLOAD_TOKEN_TTL_MINUTES,
) -> tuple[str, str]:
    settings = get_settings()
    secret_value = getattr(settings, "download_token_secret", "") or settings.webhook_secret
    secret = secret_value.encode("utf-8")
    expires_dt = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)
    expires = expires_dt.isoformat()
    payload = f"{profile}:{engine}:{expires}".encode("utf-8")
    token = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return token, expires


def _validate_upload_token(
    token: Optional[str],
    expires: Optional[str],
    profile: str,
    engine: str,
) -> None:
    settings = get_settings()
    secret_value = getattr(settings, "download_token_secret", "") or settings.webhook_secret
    secret = secret_value.encode("utf-8")
    if not token or not expires:
        raise HTTPException(status_code=401, detail="Token ausente para upload.")
    try:
        exp = datetime.fromisoformat(expires)
    except ValueError:
        raise HTTPException(status_code=401, detail="Token invalido.")
    if exp < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Token expirado.")
    payload = f"{profile}:{engine}:{expires}".encode("utf-8")
    expected = hmac.new(secret, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, token):
        raise HTTPException(status_code=401, detail="Token invalido.")




def _safe_int(value: Optional[str], default: int, minimum: int = 1, maximum: Optional[int] = None) -> int:
    try:
        parsed = int(value) if value is not None else default
    except ValueError:
        parsed = default
    if minimum is not None:
        parsed = max(parsed, minimum)
    if maximum is not None:
        parsed = min(parsed, maximum)
    return parsed


def _wants_html(request: Request) -> bool:
    accept = (request.headers.get('accept') or '').lower()
    return 'text/html' in accept or not accept


def _enforce_download_rate(session_id: Optional[str]) -> None:
    if os.getenv("OMNI_DISABLE_DOWNLOAD_RATE_LIMITS") == "1":
        return
    key = session_id or "anonymous"
    tracker = _download_tracker.setdefault(key, deque())
    now = time.time()
    while tracker and now - tracker[0] > _DOWNLOAD_RATE_WINDOW_SEC:
        tracker.popleft()
    if len(tracker) >= _DOWNLOAD_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Limite de downloads excedido.")
    tracker.append(now)


def _enforce_api_rate(key: str) -> None:
    # Não aplicar rate-limit em modo teste para não quebrar suites
    if os.getenv("TEST_MODE") == "1" or os.getenv("OMNI_TEST_MODE") == "1":
        return
    tracker = _api_rate_tracker.setdefault(key, deque())
    now = time.time()
    while tracker and now - tracker[0] > _API_RATE_WINDOW_SEC:
        tracker.popleft()
    if len(tracker) >= _API_RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Limite de requisições excedido.")
    tracker.append(now)


def _apply_filters(jobs: List[Job], status: Optional[str], profile: Optional[str], accuracy: Optional[str]) -> List[Job]:
    filtered = jobs
    if status:
        filtered = [job for job in filtered if job.status.value == status]
    if profile:
        filtered = [job for job in filtered if job.profile_id == profile]
    if accuracy == "needs_review":
        filtered = [job for job in filtered if (job.metadata or {}).get("accuracy_requires_review") == "true"]
    elif accuracy == "passing":
        filtered = [
            job
            for job in filtered
            if (job.metadata or {}).get("accuracy_requires_review") not in ("true", "True")
        ]
    return filtered


def _compute_summary(jobs: List[Job]) -> Dict[str, int]:
    summary = {
        'total': len(jobs),
        'awaiting_review': sum(1 for job in jobs if job.status == JobStatus.AWAITING_REVIEW),
        'approved': sum(1 for job in jobs if job.status == JobStatus.APPROVED),
        'failed': sum(1 for job in jobs if job.status in (JobStatus.FAILED, JobStatus.REJECTED)),
    }
    return summary


def _compute_accuracy_summary(jobs: List[Job]) -> Dict[str, Any]:
    evaluated = 0
    needs_review = 0
    passing = 0
    scores: List[float] = []
    wers: List[float] = []
    for job in jobs:
        metadata = job.metadata or {}
        score = metadata.get("accuracy_score")
        wer = metadata.get("accuracy_wer")
        status = metadata.get("accuracy_status")
        if score is None and status is None:
            continue
        evaluated += 1
        if status == "needs_review":
            needs_review += 1
        elif status == "passing":
            passing += 1
        try:
            if score is not None:
                scores.append(float(score))
        except (TypeError, ValueError):
            pass
        try:
            if wer is not None:
                wers.append(float(wer))
        except (TypeError, ValueError):
            pass
    avg_score = sum(scores) / len(scores) if scores else None
    avg_wer = sum(wers) / len(wers) if wers else None
    return {
        "evaluated": evaluated,
        "needs_review": needs_review,
        "passing": passing,
        "average_score": avg_score,
        "average_wer": avg_wer,
    }


def _get_recent_incidents(limit: int = 5) -> List[Dict[str, Any]]:
    try:
        container = get_container()
    except Exception:
        logger.warning("Falha ao instanciar container para incidentes.", exc_info=True)
        return []
    log_repo = getattr(container, 'log_repository', None)
    if not log_repo or not hasattr(log_repo, 'list_recent'):
        return []
    try:
        entries = log_repo.list_recent(limit)  # type: ignore[attr-defined]
    except Exception:
        logger.warning("Falha ao recuperar incidentes recentes.", exc_info=True)
        return []
    incidents: List[Dict[str, Any]] = []
    for entry in entries:
        incidents.append(
            {
                'job_id': entry.job_id,
                'event': entry.event,
                'level': entry.level.value,
                'message': entry.message or '',
                'timestamp': entry.timestamp.isoformat(),
                'timestamp_human': entry.timestamp.strftime('%d/%m %H:%M'),
                'icon': _LEVEL_ICON_MAP.get(entry.level.value, ''),
            }
        )
    return incidents


def _health_snapshot() -> Dict[str, Any]:
    try:
        # Reusa lógica interna sem depender do endpoint async
        settings = get_settings()
        assets_ok = Path("src/interfaces/web/static").exists() and Path("src/interfaces/web/templates").exists()
        external: Dict[str, object] = {}
        external["asr_ready"] = bool(settings.openai_api_key)
        external["chat_ready"] = bool(settings.chatgpt_api_key or settings.openai_api_key)
        try:
            probe_path = Path(settings.base_output_dir) / ".health_probe"
            probe_path.parent.mkdir(parents=True, exist_ok=True)
            probe_path.write_text("ok", encoding="utf-8")
            probe_path.unlink(missing_ok=True)
            external["storage_ready"] = True
        except Exception:
            external["storage_ready"] = False
        if os.getenv("HEALTH_PROBE_OPENAI") == "1":
            external["openai_probe"] = _probe_http(settings.openai_base_url or "", timeout_sec=2)
        degraded = not all(val for val in external.values() if isinstance(val, bool))
        return {
            "status": "degraded" if degraded else "ok",
            "external": external,
            "static_assets": assets_ok,
        }
    except Exception:
        return {"status": "unknown"}


def _compose_accuracy_snapshot(job: Job) -> Dict[str, Any]:
    metadata = job.metadata or {}
    status = metadata.get("accuracy_status")
    requires_review = metadata.get("accuracy_requires_review") == "true"
    badge = "success"
    label = "Sem medicoes"
    if status == "needs_review":
        badge = "warning"
        label = "Revisao obrigatoria"
    elif status == "passing":
        badge = "success"
        label = "Dentro da meta"
    elif status:
        badge = "info"
        label = status.replace("_", " ").title()
    def _as_float(value: Optional[str]) -> Optional[float]:
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None
    score = _as_float(metadata.get("accuracy_score"))
    baseline = _as_float(metadata.get("accuracy_baseline"))
    penalty = _as_float(metadata.get("accuracy_penalty"))
    wer = _as_float(metadata.get("accuracy_wer"))
    updated_at = metadata.get("accuracy_updated_at")
    display_score = f"{score * 100:.2f}%" if score is not None else "N/A"
    display_wer = f"{wer * 100:.2f}%" if wer is not None else "N/A"
    source = metadata.get("accuracy_reference_source") or "asr_output"
    return {
        "raw": metadata,
        "status": status,
        "badge": badge,
        "label": label,
        "requires_review": requires_review,
        "score": display_score,
        "wer": display_wer,
        "baseline": f"{baseline * 100:.2f}%" if baseline is not None else "N/A",
        "penalty": f"{penalty * 100:.2f}%" if penalty is not None else "N/A",
        "updated_at": updated_at,
        "reference_source": source,
    }


def _summarize_session(session: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    if not session:
        return None
    metadata = session.get('metadata') or {}
    session_id = str(session.get('session_id') or '') or metadata.get('state') or ''
    suffix = session_id[-4:].upper() if session_id else 'AUTH'
    label = metadata.get('display_name') or f"Sessao {suffix}"
    created_at = session.get('created_at')
    caption = "Sessao ativa"
    if isinstance(created_at, (int, float)):
        dt = datetime.fromtimestamp(created_at, tz=timezone.utc)
        caption = f"Desde {dt.strftime('%H:%M:%S')} UTC"
    initials = ''.join(ch for ch in label if ch.isalpha()).upper()[:2] or 'TF'
    return {
        'label': label,
        'caption': caption,
        'initials': initials,
    }


def _get_job_logs(job_id: str) -> List[LogEntry]:
    try:
        container = get_container()
    except Exception:
        logger.warning('Falha ao instanciar container para logs.', exc_info=True)
        return []
    if not hasattr(container, 'log_repository'):
        return []
    entries = container.log_repository.list_by_job(job_id)  # type: ignore[attr-defined]
    sorted_entries = sorted(entries, key=lambda entry: entry.timestamp, reverse=True)
    return sorted_entries


def _export_logs(job_id: str, logs: List[LogEntry], export_format: str) -> Response:
    filename = f"{job_id}_logs"
    content = ""
    if export_format == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['timestamp', 'level', 'event', 'message'])
        for entry in logs:
            writer.writerow([
                entry.timestamp.isoformat(),
                entry.level.value,
                entry.event,
                entry.message or '',
            ])
        content = output.getvalue()
    elif export_format == 'json':
        data = [
            {
                'timestamp': entry.timestamp.isoformat(),
                'level': entry.level.value,
                'event': entry.event,
                'message': entry.message,
            }
            for entry in logs
        ]
        return JSONResponse(data)
    return Response(
        content=content,
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}.csv"'},
    )


def _format_template_label(updated_at: Optional[str]) -> str:
    if not updated_at:
        return "Formato nunca atualizado."
    try:
        timestamp = datetime.fromisoformat(updated_at)
        return f"Atualizado s {timestamp.strftime('%H:%M:%S')}"
    except ValueError:
        return "Atualizao registrada."


def _normalize_template_id(value: str) -> str:
    slug = (value or "").strip().lower()
    if not slug or not _TEMPLATE_ID_PATTERN.match(slug):
        raise HTTPException(status_code=400, detail="Identificador deve conter letras/nmeros e traos.")
    return slug


def _normalize_locale_code(value: str) -> Optional[str]:
    if not value:
        return None
    slug = value.strip()
    if not _LOCALE_PATTERN.match(slug):
        raise HTTPException(status_code=400, detail="Locale invalido. Use padrao pt-BR, en-US, etc.")
    return slug.replace("_", "-").lower()


def _compose_template_file(template_id: str, name: str, description: str, body: str, locale: Optional[str] = None) -> str:
    metadata = {"id": template_id, "name": name, "description": description}
    if locale:
        metadata["locale"] = locale
    yaml_block = yaml.safe_dump(metadata, allow_unicode=True).strip()
    return f"---\n{yaml_block}\n---\n{body.strip()}\n"


def _build_preview_context() -> Dict[str, str]:
    return {
        "header": "Arquivo original: exemplo.wav\nPerfil editorial: preview",
        "transcript": "Este e um trecho de demonstracao para validar o layout final do template.",
        "job_id": "preview-job",
        "profile_id": "preview-profile",
        "language": "pt-BR",
    }


def _render_template_body(body: str, context: Dict[str, str]) -> str:
    pattern = re.compile(r"{{\s*([\w\.]+)\s*}}")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return context.get(key, "")

    return pattern.sub(replace, body.strip()).strip()


def _probe_http(url: str, timeout_sec: int = 2) -> bool:
    if not url:
        return False
    try:
        resp = requests.get(url, timeout=timeout_sec)
        return resp.status_code < 500
    except Exception:
        return False


def _append_template_audit(action: str, template_id: str, metadata: Dict[str, Any] | None = None) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "template_id": template_id,
        "metadata": metadata or {},
    }
    _template_audit_path.parent.mkdir(parents=True, exist_ok=True)
    with _template_audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _load_template_audit(limit: int = 20) -> List[Dict[str, Any]]:
    if not _template_audit_path.exists():
        return []
    lines = _template_audit_path.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for raw in reversed(lines):
        try:
            entries.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
        if len(entries) >= limit:
            break
    return entries


def _available_template_locales() -> List[str]:
    registry = _get_template_registry()
    locales = {template.locale for template in registry.list_templates() if template.locale}
    return sorted(locale for locale in locales if locale)


def _guess_locale(language: Optional[str]) -> Optional[str]:
    if not language:
        return None
    normalized = language.replace("_", "-")
    if _LOCALE_PATTERN.match(normalized):
        return normalized
    return None

def _resolve_logo_path() -> Optional[Path]:
    if not _BRANDING_DIR.exists():
        return None
    for ext in _ALLOWED_LOGO_EXTS:
        candidate = _BRANDING_DIR / f"logo{ext}"
        if candidate.exists():
            return candidate
    return None


@app.get("/branding/logo")
async def get_branding_logo() -> Response:
    path = _resolve_logo_path()
    if not path:
        raise HTTPException(status_code=404, detail="Logomarca nao definida.")
    return FileResponse(path)


@app.post("/settings/branding/logo")
async def upload_branding_logo(
    request: Request,
    logo: UploadFile = File(...),
    _: dict | None = Depends(require_active_session),
) -> Response:
    ext = Path(logo.filename or "").suffix.lower()
    if ext not in _ALLOWED_LOGO_EXTS:
        raise HTTPException(status_code=400, detail="Formato de logo nao suportado.")
    _BRANDING_DIR.mkdir(parents=True, exist_ok=True)
    for old_ext in _ALLOWED_LOGO_EXTS:
        try:
            (_BRANDING_DIR / f"logo{old_ext}").unlink(missing_ok=True)
        except OSError:
            continue
    content = await logo.read()
    if not content:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")
    target = _BRANDING_DIR / f"logo{ext}"
    target.write_bytes(content)
    flash = "branding-updated"
    if "application/json" in (request.headers.get("accept") or "").lower():
        return JSONResponse({"status": "ok", "flash": flash})
    return RedirectResponse("/?flash=branding-updated", status_code=303)



