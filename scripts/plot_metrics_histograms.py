#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import os
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, Tuple

try:  # Optional dependency for visualization
    import matplotlib.pyplot as plt
except ImportError:  # pragma: no cover
    plt = None


def parse_event_key(key: str) -> Tuple[str, Dict[str, str]]:
    """Retorna (event_name, tags dict)."""
    parts = key.split("|")
    name = parts[0]
    tags = {}
    for part in parts[1:]:
        if "=" not in part:
            continue
        tag_name, tag_value = part.split("=", 1)
        tags[tag_name] = tag_value
    return name, tags


def load_histograms(path: Path) -> Dict[str, Dict[str, int]]:
    content = path.read_text(encoding="utf-8")
    return json.loads(content)


def bucket_midpoint(label: str, bucket_size: float) -> float:
    try:
        bucket = float(label)
    except ValueError:
        return float("nan")
    return bucket + bucket_size / 2


def aggregate_buckets(buckets: Dict[str, int], bucket_size: float) -> Iterable[Tuple[float, int]]:
    for bucket_label, count in buckets.items():
        yield bucket_midpoint(bucket_label, bucket_size), count


def summarize(buckets: Dict[str, int], bucket_size: float) -> Dict[str, float]:
    data = []
    for point, count in aggregate_buckets(buckets, bucket_size):
        data.extend([point] * count)
    if not data:
        return {}
    data.sort()
    return {
        "count": len(data),
        "mean": sum(data) / len(data),
        "p50": data[int(len(data) * 0.5) - 1],
        "p95": data[int(len(data) * 0.95) - 1],
        "p99": data[int(len(data) * 0.99) - 1],
    }


def plot_histogram(buckets: Dict[str, int], bucket_size: float, title: str, output: Path | None = None) -> None:
    if plt is None:
        return
    points = []
    counts = []
    for point, count in sorted(aggregate_buckets(buckets, bucket_size), key=lambda pair: pair[0]):
        points.append(point)
        counts.append(count)
    if not points:
        return
    plt.figure(figsize=(10, 4))
    plt.bar(points, counts, width=bucket_size * 0.9, align="center")
    plt.title(title)
    plt.xlabel("Milissegundos")
    plt.ylabel("Ocorrências")
    plt.grid(True, axis="y", alpha=0.4)
    if output:
        plt.tight_layout()
        plt.savefig(output, dpi=120)
        print(f"Gráfico salvo em {output}")
    else:
        plt.tight_layout()
        plt.show()


def find_event(histograms: Dict[str, Dict[str, int]], event: str, filters: Dict[str, str]) -> Iterable[Tuple[str, Dict[str, int], Dict[str, str]]]:
    for key, bucket_map in histograms.items():
        name, tags = parse_event_key(key)
        if name != event:
            continue
        if all(tags.get(k) == v for k, v in filters.items()):
            yield key, bucket_map, tags


def main() -> None:
    parser = argparse.ArgumentParser(description="Explorar os histogramas gerados pelo metrics_logger.")
    parser.add_argument("--file", "-f", type=Path, default=Path("logs/metrics_histograms.json"), help="JSON gerado pelo metrics_logger.")
    parser.add_argument("--event", "-e", required=True, help="Nome do evento, ex.: pipeline.stage.latency")
    parser.add_argument("--stage", "-s", help="Filtra pelo valor da tag `stage`.")
    parser.add_argument("--success", choices=["true", "false"], help="Filtra pela tag `success`.")
    parser.add_argument("--bucket", type=float, default=50.0, help="Bucket size esperado (ms).")
    parser.add_argument("--preview", action="store_true", help="Mostrar gráfico com matplotlib (se disponível).")
    parser.add_argument("--output", "-o", type=Path, help="Salvar gráfico em arquivo.")
    args = parser.parse_args()

    if not args.file.exists():
        raise SystemExit(f"Nenhum histograma encontrado em {args.file}.")

    histograms = load_histograms(args.file)
    filters = {}
    if args.stage:
        filters["stage"] = args.stage
    if args.success:
        filters["success"] = args.success

    selected = list(find_event(histograms, args.event, filters))
    if not selected:
        raise SystemExit("Nenhum evento encontrado para os filtros fornecidos.")

    for key, buckets, tags in selected:
        print("=" * 60)
        print(f"Evento: {key}")
        print(f"Tags: {tags}")
        summary = summarize(buckets, args.bucket)
        if not summary:
            print("Sem buckets registrados.")
            continue
        print(f"Eventos totais: {summary['count']}")
        print(f"   p50: {summary['p50']:.2f} ms, p95: {summary['p95']:.2f} ms, p99: {summary['p99']:.2f} ms")
        print(f"   Média: {summary['mean']:.2f} ms")
        if args.preview:
            title = f"{args.event} ({tags})"
            plot_histogram(buckets, args.bucket, title, args.output)


if __name__ == "__main__":
    main()
