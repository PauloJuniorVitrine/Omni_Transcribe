from __future__ import annotations

"""
Gera o schema OpenAPI da aplicação FastAPI e salva em artifacts/openapi.json.
Usado em testes de contrato frontend↔backend e em jobs de CI.
"""

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
for candidate in (ROOT, SRC):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from interfaces.http.app import app  # noqa: E402

OUTPUT_PATH = Path("artifacts/openapi.json")


def generate_openapi_schema(output_path: Path = OUTPUT_PATH) -> dict:
    """
    Exporta o schema OpenAPI atual para o caminho indicado.
    Retorna o payload já carregado como dict.
    """
    client = TestClient(app)
    response = client.get("/openapi.json")
    response.raise_for_status()
    schema = response.json()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")
    return schema


if __name__ == "__main__":
    schema = generate_openapi_schema()
    print(f"OpenAPI schema salvo em {OUTPUT_PATH} com {len(schema.get('paths', {}))} rotas.")
