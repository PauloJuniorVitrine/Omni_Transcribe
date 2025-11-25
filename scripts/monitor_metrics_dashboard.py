#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, Tuple

try:  # Optional plotting support
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    plt = None


def load_json(path: Path) -> Dict[str, Dict[str, int]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def stage_from_key(key: str) -> Tuple[str, Dict[str, str]]:
    parts = key.split("|")
    name = parts[0]
    tags: Dict[str, str] = {}
    for tail in parts[1:]:
        if "=" not in tail:
            continue
        k, v = tail.split("=", 1)
        tags[k] = v
    return name, tags


def percentile_from_buckets(buckets: Dict[str, int], bucket_size: float) -> Dict[str, float]:
    measurements: list[float] = []
    for bucket_label, count in buckets.items():
        try:
            bucket_start = float(bucket_label)
        except ValueError:
            continue
        midpoint = bucket_start + bucket_size / 2
        measurements.extend([midpoint] * count)
    if not measurements:
        return {}
    measurements.sort()
    def pick(p: float) -> float:
        index = min(len(measurements) - 1, max(0, int(len(measurements) * p) - 1))
        return measurements[index]

    return {
        "count": len(measurements),
        "mean": statistics.mean(measurements),
        "p50": pick(0.5),
        "p95": pick(0.95),
        "p99": pick(0.99),
    }


def summarize_histograms(histograms: Dict[str, Dict[str, int]], bucket_size: float) -> Dict[str, Dict[str, float]]:
    summary: Dict[str, Dict[str, float]] = {}
    for key, buckets in histograms.items():
        name, tags = stage_from_key(key)
        if name != "pipeline.stage.latency":
            continue
        stage = tags.get("stage", "unknown")
        stats = percentile_from_buckets(buckets, bucket_size)
        if stats:
            summary[stage] = stats
    return summary


def load_alerts(path: Path) -> Iterable[Dict[str, str]]:
    if not path.exists():
        return []
    alerts = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            alerts.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return alerts


def plot_summary(summary: Dict[str, Dict[str, float]], output: Path | None = None) -> None:
    if plt is None or not summary:
        return
    stages = list(summary.keys())
    p95 = [summary[stage]["p95"] for stage in stages]
    plt.figure(figsize=(8, 4))
    plt.bar(stages, p95, color="tab:blue")
    plt.title("p95 de pipeline.stage.latency por etapa")
    plt.ylabel("ms")
    plt.tight_layout()
    if output:
        plt.savefig(output, dpi=120)
        print(f"Gráfico salvo em {output}")
    else:
        plt.show()


def main() -> None:
    parser = argparse.ArgumentParser(description="Painel rápido de métricas + alertas.")
    parser.add_argument("--histogram", type=Path, default=Path("logs/metrics_histograms.json"))
    parser.add_argument("--alerts", type=Path, default=Path("logs/alerts.log"))
    parser.add_argument("--bucket", type=float, default=50.0, help="Tamanho do bucket em ms.")
    parser.add_argument("--preview", action="store_true", help="Exibir gráfico (matplotlib).")
    parser.add_argument("--output", type=Path, help="Salvar gráfico.")
    args = parser.parse_args()

    histograms = load_json(args.histogram)
    summary = summarize_histograms(histograms, args.bucket)
    print("=" * 60)
    print("Resumo de pipeline.stage.latency (p50/p95/p99)")
    for stage, stats in summary.items():
        print(f"  - {stage}: p50={stats['p50']:.1f}ms, p95={stats['p95']:.1f}ms, p99={stats['p99']:.1f}ms, count={int(stats['count'])}")
    if args.preview:
        plot_summary(summary, args.output)

    alerts = list(load_alerts(args.alerts))
    counter = Counter(alert.get("event", "unknown") for alert in alerts)
    print("\nAlertas recentes (logs/alerts.log):")
    for event, count in counter.most_common():
        print(f"  - {event}: {count}")


if __name__ == "__main__":
    main()
