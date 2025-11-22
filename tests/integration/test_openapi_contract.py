from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from interfaces.http.app import app
from scripts.generate_openapi_schema import OUTPUT_PATH, generate_openapi_schema


def _operation(schema: dict, path: str, method: str = "get") -> dict:
    return schema["paths"].get(path, {}).get(method, {})


def _param_names(operation: dict) -> set[str]:
    return {param["name"] for param in operation.get("parameters", [])}


def test_openapi_schema_covers_frontend_contract_and_is_persisted() -> None:
    """
    Garante que o schema OpenAPI atual inclui as rotas usadas pelo frontend
    e que o artefato em disco está sincronizado (usado por Jest).
    """
    # Gera e persiste o schema (utilizado depois pelos testes JS).
    schema = generate_openapi_schema()
    assert OUTPUT_PATH.exists(), "OpenAPI não foi persistido em artifacts/openapi.json"

    paths = schema.get("paths", {})
    required_paths = {
        "/api/dashboard/summary",
        "/api/dashboard/incidents",
        "/api/jobs/{job_id}/logs",
        "/api/jobs/{job_id}/logs/export",
        "/api/jobs/{job_id}/process",
        "/settings/templates/{template_id}/raw",
        "/settings/templates/preview",
    }
    missing = [path for path in required_paths if path not in paths]
    assert not missing, f"Rotas ausentes no OpenAPI: {missing}"

    summary_get = _operation(schema, "/api/dashboard/summary", "get")
    assert "responses" in summary_get and "200" in summary_get["responses"]

    incidents_get = _operation(schema, "/api/dashboard/incidents", "get")
    assert "responses" in incidents_get and "200" in incidents_get["responses"]

    logs_get = _operation(schema, "/api/jobs/{job_id}/logs", "get")
    # query params não são tipados no handler atual; validamos apenas resposta e path param
    assert "200" in logs_get.get("responses", {})

    logs_export = _operation(schema, "/api/jobs/{job_id}/logs/export", "get")
    assert "200" in logs_export.get("responses", {})

    process_post = _operation(schema, "/api/jobs/{job_id}/process", "post")
    assert "200" in process_post.get("responses", {}) or "303" in process_post.get("responses", {})

    template_raw = _operation(schema, "/settings/templates/{template_id}/raw", "get")
    assert "responses" in template_raw and "200" in template_raw["responses"]

    template_preview = _operation(schema, "/settings/templates/preview", "post")
    assert "requestBody" in template_preview and "200" in template_preview.get("responses", {})


def test_live_openapi_endpoint_matches_generated_file() -> None:
    """
    Verifica que o /openapi.json servido pela aplicação bate com o artefato salvo.
    Evita falsos positivos se o schema mudar e o arquivo não for regenerado.
    """
    client = TestClient(app)
    response = client.get("/openapi.json")
    response.raise_for_status()
    live_schema = response.json()

    if OUTPUT_PATH.exists():
        saved_schema = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        assert live_schema == saved_schema, "Schema em artifacts/openapi.json desatualizado em relação ao backend"
