from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse

from application.services.oauth_service import OAuthService
from application.services.session_service import SessionService
from config import Settings
from .dependencies import get_app_settings, get_session_service


router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("transcribeflow.auth")


def get_oauth_service(settings: Settings = Depends(get_app_settings)) -> OAuthService:
    return OAuthService(settings)


@router.get("/login")
async def login(oauth_service: OAuthService = Depends(get_oauth_service)) -> dict:
    auth_payload = oauth_service.build_authorization_url()
    logger.info("Solicitando login OAuth", extra={"state": auth_payload["state"]})
    return auth_payload


@router.get("/login/browser")
async def login_browser(oauth_service: OAuthService = Depends(get_oauth_service)) -> RedirectResponse:
    auth_payload = oauth_service.build_authorization_url()
    logger.info("Redirecionando login OAuth", extra={"state": auth_payload["state"]})
    return RedirectResponse(auth_payload["url"], status_code=302)


@router.get("/callback")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    oauth_service: OAuthService = Depends(get_oauth_service),
    session_service: SessionService = Depends(get_session_service),
):
    if not code:
        raise HTTPException(status_code=400, detail="Código não fornecido.")
    tokens = oauth_service.exchange_code(code)
    session_id = session_service.create_session(tokens, metadata={"state": state})
    logger.info("Callback OAuth recebido", extra={"state": state, "session_id": session_id})
    expects_json = "application/json" in (request.headers.get("accept") or "")
    if expects_json:
        response = JSONResponse({"message": "OAuth callback processado", "tokens": tokens})
    else:
        response = RedirectResponse("/?flash=login-success", status_code=303)
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        max_age=session_service.ttl_seconds,
        samesite="lax",
    )
    return response
