from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from application.services.webhook_service import WebhookService, WebhookValidationError
from config import Settings
from .dependencies import get_app_settings, get_webhook_service


router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger("transcribeflow.webhooks")


@router.post("/external")
async def receive_webhook(
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    x_timestamp: str | None = Header(default=None, alias="X-Signature-Timestamp"),
    integration_id: str = Header(default="external", alias="X-Integration-Id"),
    webhook_service: WebhookService = Depends(get_webhook_service),
    settings: Settings = Depends(get_app_settings),
) -> Dict[str, Any]:
    body = await request.body()
    try:
        result = webhook_service.verify(
            body,
            x_signature,
            integration=integration_id,
            timestamp_header=x_timestamp,
        )
    except WebhookValidationError as exc:
        logger.warning(
            "Webhook rejeitado",
            extra={"integration": integration_id, "reason": str(exc)},
        )
        raise HTTPException(status_code=401, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception(
            "Erro inesperado ao validar webhook",
            extra={"integration": integration_id},
        )
        detail = str(exc) if settings.app_env == "test" else "Erro interno"
        raise HTTPException(status_code=500, detail=detail) from exc

    metrics = webhook_service.snapshot_metrics()
    logger.info(
        "Webhook aceito",
        extra={
            "trace_id": result.trace_id,
            "integration": integration_id,
            "bytes": len(body),
            "latency_ms": result.latency_ms,
            "metrics": metrics,
        },
    )
    return {"status": "received", "trace_id": result.trace_id, "latency_ms": result.latency_ms}
