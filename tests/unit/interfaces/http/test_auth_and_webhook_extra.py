import pytest
from fastapi import HTTPException

from interfaces.http import auth_routes, webhook_routes
from application.services.webhook_service import WebhookValidationError


@pytest.mark.asyncio
async def test_auth_callback_missing_code_raises():
    with pytest.raises(HTTPException) as exc:
        req = type("Req", (), {"headers": {}, "state": type("S", (), {"trace_id": ""})()})()
        await auth_routes.callback(code=None, state="s", request=req)  # type: ignore[arg-type]
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_auth_callback_missing_state_raises():
    with pytest.raises(HTTPException) as exc:
        req = type("Req", (), {"headers": {}, "state": type("S", (), {"trace_id": ""})()})()
        await auth_routes.callback(code="c", state=None, request=req)  # type: ignore[arg-type]
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_auth_callback_internal_error_returns_500(monkeypatch):
    class _OAuth:
        def exchange_code(self, _code):
            raise RuntimeError("boom")

    class _Session:
        def create_session(self, *_args, **_kwargs):
            return "sess"
        ttl_seconds = 10

    class _Settings:
        app_env = "test"

    with pytest.raises(HTTPException) as exc:
        await auth_routes.callback(  # type: ignore[arg-type]
            request=type("Req", (), {"headers": {}, "state": type("S", (), {"trace_id": ""})})(),
            code="c",
            state="s",
            oauth_service=_OAuth(),
            session_service=_Session(),
            settings=_Settings(),
        )
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_webhook_returns_401_on_validation_error(monkeypatch):
    class _Webhook:
        def verify(self, *_args, **_kwargs):
            raise WebhookValidationError("bad")

        def snapshot_metrics(self):
            return {}

    class _Settings:
        app_env = "prod"

    class _Req:
        async def body(self):
            return b"payload"

    with pytest.raises(HTTPException) as exc:
        await webhook_routes.receive_webhook(
            request=_Req(),  # type: ignore[arg-type]
            x_signature="sig",
            x_timestamp="ts",
            integration_id="ext",
            webhook_service=_Webhook(),
            settings=_Settings(),
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_webhook_returns_500_on_generic_error(monkeypatch):
    class _Webhook:
        def verify(self, *_args, **_kwargs):
            raise RuntimeError("oops")

        def snapshot_metrics(self):
            return {}

    class _Settings:
        app_env = "production"

    class _Req:
        async def body(self):
            return b"payload"

    with pytest.raises(HTTPException) as exc:
        await webhook_routes.receive_webhook(
            request=_Req(),  # type: ignore[arg-type]
            x_signature="sig",
            x_timestamp="ts",
            integration_id="ext",
            webhook_service=_Webhook(),
            settings=_Settings(),
        )
    assert exc.value.status_code == 500
