from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

try:  # Optional dependency
    import requests  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback when requests is unavailable
    requests = None


METRICS_PATH = Path("logs/metrics.log")
ALERTS_PATH = Path("logs/alerts.log")
HISTOGRAM_PATH = Path("logs/metrics_histograms.json")
_ALERT_WEBHOOK_URLS = [
    url.strip() for url in os.getenv("ALERT_WEBHOOK_URL", "").split(",") if url.strip()
]
_METRIC_WEBHOOK_URLS = [
    url.strip() for url in os.getenv("METRICS_WEBHOOK_URL", "").split(",") if url.strip()
]


def record_metric(event: str, payload: Dict[str, Any]) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "payload": payload,
    }
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("a", encoding="utf-8") as cursor:
        cursor.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _post_webhooks(_METRIC_WEBHOOK_URLS, entry)


def notify_alert(event: str, payload: Dict[str, Any]) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "payload": payload,
    }
    _post_webhooks(_ALERT_WEBHOOK_URLS, entry)
    ALERTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ALERTS_PATH.open("a", encoding="utf-8") as cursor:
        cursor.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_entries(limit: int | None = None) -> list[Dict[str, Any]]:
    if not METRICS_PATH.exists():
        return []
    lines = METRICS_PATH.read_text(encoding="utf-8").splitlines()
    if limit:
        lines = lines[-limit:]
    entries: list[Dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def summarize_metrics() -> Dict[str, Any]:
    entries = load_entries()
    summary: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        name = entry.get("event", "unknown")
        summary.setdefault(name, {"count": 0, "last_timestamp": None})
        summary[name]["count"] += 1
        summary[name]["last_timestamp"] = entry.get("timestamp")
    return summary


def _post_webhooks(urls: Iterable[str], payload: Dict[str, Any]) -> None:
    if not urls or not requests:
        return
    for url in urls:
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception:
            continue


def record_histogram(
    name: str,
    value: float,
    bucket_size: float = 50.0,
    tags: Dict[str, object] | None = None,
) -> None:
    histogram = _load_histograms()
    tags = tags or {}
    tag_key = ",".join(f"{key}={tags[key]}" for key in sorted(tags))
    bucket = int(value // bucket_size * bucket_size)
    event_key = f"{name}|bucket_size={bucket_size}|{tag_key or 'default'}"
    buckets = histogram.get(event_key, {})
    bucket_label = str(bucket)
    buckets[bucket_label] = buckets.get(bucket_label, 0) + 1
    histogram[event_key] = buckets
    _save_histograms(histogram)


def load_histograms() -> Dict[str, Dict[str, int]]:
    return _load_histograms()


def _load_histograms() -> Dict[str, Dict[str, int]]:
    if not HISTOGRAM_PATH.exists():
        return {}
    try:
        return json.loads(HISTOGRAM_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_histograms(data: Dict[str, Dict[str, int]]) -> None:
    HISTOGRAM_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTOGRAM_PATH.open("w", encoding="utf-8") as cursor:
        cursor.write(json.dumps(data, ensure_ascii=False, indent=2))


__all__ = [
    "record_metric",
    "notify_alert",
    "load_entries",
    "summarize_metrics",
    "record_histogram",
    "load_histograms",
]
