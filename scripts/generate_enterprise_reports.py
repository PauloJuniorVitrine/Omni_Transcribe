#!/usr/bin/env python
"""
Gera arquivos Enterprise+ (feature flags, antipadrões, resiliência) de forma reproduzível.

Uso:
    python scripts/generate_enterprise_reports.py --exec-id 20251113T103533Z_MSJTU6
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from textwrap import dedent

FLAG_METADATA = {
    "dashboard.live_summary": {
        "backend": "Dashboard usa resumo dinâmico",
        "frontend": "Polling JS em `jobs.html`",
    },
    "dashboard.live_incidents": {
        "backend": "Endpoint sempre disponível",
        "frontend": "Painel visível quando flag on",
    },
    "jobs.manual_reprocess": {
        "backend": "Rota `/jobs/{id}/process`",
        "frontend": "Formulário AJAX exibido só quando on",
    },
    "ui.api_settings": {
        "backend": "Rota retorna 404 se flag off",
        "frontend": "Link deve ser ocultado quando off",
    },
}

FRONT_VISIBILITY = {
    "dashboard.live_summary": {
        "on": "Cards atualizados em tempo real.",
        "off": "Cards exibem dados estáticos.",
    },
    "dashboard.live_incidents": {
        "on": "Lista dinâmica de incidentes com badge.",
        "off": "Mensagem informando monitoramento desativado.",
    },
    "jobs.manual_reprocess": {
        "on": "Formulário AJAX e status visível.",
        "off": "Seção oculta; logs continuam acessíveis.",
    },
    "ui.api_settings": {
        "on": "Página de credenciais acessível.",
        "off": "Rota 404; menu deve ocultar link.",
    },
}

ANTIPATTERNS = [
    ("Controller gordo", "src/interfaces/http/app.py", "SRP violado"),
    ("Segredos em JSON", "config/runtime_credentials.py", "Mitigado com criptografia"),
]

RESILIENCE = [
    ("Dashboard", "Polling + fallback de status", "Médio"),
    ("Downloads", "Token HMAC (flag opcional)", "Alto"),
]


def load_flags() -> dict[str, bool]:
    path = Path("config/feature_flags.json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8-sig"))
    return {}


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def generate_feature_flag_docs(exec_id: str) -> None:
    flags = load_flags()
    diff_lines = ["# Feature Flag Contract Diff – EXEC_ID {exec}".format(exec=exec_id), ""]
    diff_lines.append("| Flag | Default | Backend Uso | Frontend Uso | Status atual |")
    diff_lines.append("| --- | --- | --- | --- | --- |")
    for name, meta in FLAG_METADATA.items():
        diff_lines.append(
            f"| `{name}` | {str(flags.get(name, True)).lower()} | {meta['backend']} | "
            f"{meta['frontend']} | {'on' if flags.get(name, True) else 'off'} |"
        )
    write_file(
        Path(f"docs/feature_flag_contract_diff_{exec_id}.md"),
        "\n".join(diff_lines),
    )

    front_lines = ["# Front Visibility vs Feature Flags – EXEC_ID {exec}".format(exec=exec_id), ""]
    front_lines.append("| Flag | ON | OFF |")
    front_lines.append("| --- | --- | --- |")
    for name, meta in FRONT_VISIBILITY.items():
        front_lines.append(f"| `{name}` | {meta['on']} | {meta['off']} |")
    write_file(
        Path(f"docs/front_visibility_vs_flag_{exec_id}.md"),
        "\n".join(front_lines),
    )


def generate_antipatterns(exec_id: str) -> None:
    lines = ["# Antipatterns Detected – EXEC_ID {exec}".format(exec=exec_id), ""]
    lines.append("| Tipo | Local | Status |")
    lines.append("| --- | --- | --- |")
    for item in ANTIPATTERNS:
        lines.append(f"| {item[0]} | {item[1]} | {item[2]} |")
    write_file(Path(f"docs/antipatterns_detected_{exec_id}.md"), "\n".join(lines))


def generate_resilience(exec_id: str) -> None:
    lines = ["# Resilience Matrix – EXEC_ID {exec}".format(exec=exec_id), ""]
    lines.append("| Área | Mitigação | Sensibilidade |")
    lines.append("| --- | --- | --- |")
    for area, mitigation, risk in RESILIENCE:
        lines.append(f"| {area} | {mitigation} | {risk} |")
    write_file(Path(f"docs/resilience_matrix_{exec_id}.md"), "\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera relatórios Enterprise+.")
    parser.add_argument("--exec-id", required=False, help="Identificador da execução.")
    args = parser.parse_args()
    exec_id = args.exec_id or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ_AUTOGEN")
    generate_feature_flag_docs(exec_id)
    generate_antipatterns(exec_id)
    generate_resilience(exec_id)
    print(f"Relatórios Enterprise+ gerados para {exec_id}.")


if __name__ == "__main__":
    main()
