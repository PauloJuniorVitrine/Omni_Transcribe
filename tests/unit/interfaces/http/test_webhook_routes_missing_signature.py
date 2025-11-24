from __future__ import annotations

from fastapi.testclient import TestClient

from interfaces.http.app import app


def test_webhook_route_missing_signature_returns_401():
    client = TestClient(app)
    resp = client.post("/webhooks/external", content=b"payload")
    assert resp.status_code == 401
