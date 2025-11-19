#!/usr/bin/env python
"""
Lê logs/metrics.log e gera relatório integration_metrics_X.md + observability_comparison_X.md.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import List, Dict

METRICS_PATH = Path("logs/metrics.log")


def load_entries() -> List[Dict[str, str]]:
    if not METRICS_PATH.exists():
        return []
    entries = []
    for line in METRICS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera relatórios de métricas de integração.")
    parser.add_argument("--exec-id", required=False)
    args = parser.parse_args()
    exec_id = args.exec_id or datetime.utcnow().strftime("%Y%m%dT%H%M%SZ_AUTOGEN")
    entries = load_entries()
    counter = Counter(entry["event"] for entry in entries)
    rows = ["# Integration Metrics – EXEC_ID {exec}".format(exec=exec_id), ""]
    rows.append("| Evento | Ocorrências | Última amostra |")
    rows.append("| --- | --- | --- |")
    for event, count in counter.items():
        latest = next(
            (entry["timestamp"] for entry in reversed(entries) if entry["event"] == event),
            "-",
        )
        rows.append(f"| {event} | {count} | {latest} |")
    write_file(Path(f"docs/integration_metrics_{exec_id}.md"), "\n".join(rows))

    comp = ["# Observability Comparison – EXEC_ID {exec}".format(exec=exec_id), ""]
    comp.append(
        "Baseado nos eventos coletados em `logs/metrics.log`. "
        "Recomenda-se comparar com dados dos APMs externos assim que disponíveis."
    )
    write_file(Path(f"docs/observability_comparison_{exec_id}.md"), "\n".join(comp))
    print(f"Métricas geradas para {exec_id}.")


if __name__ == "__main__":
    main()
