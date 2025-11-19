from __future__ import annotations

import json
from pathlib import Path

import pytest

from infrastructure.telemetry.metrics_logger import (
    _post_webhooks,
    load_entries,
    notify_alert,
    record_metric,
    summarize_metrics,
)


def test_record_metric_writes_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "")
    monkeypatch.setenv("METRICS_WEBHOOK_URL", "")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", "0")  # prevent inheriting envs
    metrics_path = tmp_path / "metrics.log"
    alerts_path = tmp_path / "alerts.log"
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.METRICS_PATH", metrics_path)
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.ALERTS_PATH", alerts_path)

    record_metric("test.event", {"value": 42})

    lines = metrics_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "test.event"
    assert payload["payload"]["value"] == 42
    entries = load_entries()
    assert len(entries) == 1
    summary = summarize_metrics()
    assert summary["test.event"]["count"] == 1


def test_notify_alert_appends_and_falls_back(tmp_path, monkeypatch):
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.requests", None)
    metrics_path = tmp_path / "metrics.log"
    alerts_path = tmp_path / "alerts.log"
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.METRICS_PATH", metrics_path)
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.ALERTS_PATH", alerts_path)

    notify_alert("alert.event", {"status": "critical"})
    payload = json.loads(alerts_path.read_text(encoding="utf-8").strip())
    assert payload["event"] == "alert.event"
    assert payload["payload"]["status"] == "critical"


def test_post_webhooks_handles_success_and_errors(monkeypatch, tmp_path):
    metrics_path = tmp_path / "metrics.log"
    alerts_path = tmp_path / "alerts.log"
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.METRICS_PATH", metrics_path)
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.ALERTS_PATH", alerts_path)
    calls: list[tuple[str, dict]] = []

    class DummyRequests:
        def post(self, url, json, timeout):
            calls.append((url, json))
            if "fail" in url:
                raise RuntimeError("network error")

    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.requests", DummyRequests())
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger._METRIC_WEBHOOK_URLS", ["https://ok", "https://fail"])
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger._ALERT_WEBHOOK_URLS", ["https://ok-alert"])

    record_metric("event.metric", {"value": 1})
    notify_alert("event.alert", {"value": 2})

    assert any(url == "https://ok" for url, _ in calls)
    assert any(url == "https://fail" for url, _ in calls)
    assert any(url == "https://ok-alert" for url, _ in calls)


def test_load_entries_limits_and_skips_invalid(tmp_path, monkeypatch):
    metrics_path = tmp_path / "metrics.log"
    monkeypatch.setattr("infrastructure.telemetry.metrics_logger.METRICS_PATH", metrics_path)
    metrics_path.write_text('{"event": "a"}\ninvalid\n{"event": "b"}\n', encoding="utf-8")

    entries = load_entries(limit=2)

    assert len(entries) == 1
    assert entries[0]["event"] == "b"


def test_report_accuracy_metrics_stream(tmp_path, monkeypatch):
    metrics_path = tmp_path / "metrics.log"
    monkeypatch.setattr("scripts.report_accuracy_metrics.METRICS_PATH", metrics_path)
    monkeypatch.setattr("scripts.report_accuracy_metrics.OUTPUT_PATH", tmp_path / "report.md")
    entries = [
        {
            "timestamp": "2025-01-01T00:00:00Z",
            "event": "accuracy.guard.evaluated",
            "payload": {"job_id": f"job-{idx}", "score": 0.99, "requires_review": False, "baseline": 0.99, "wer_active": 0.01},
        }
        for idx in range(5)
    ]
    metrics_path.write_text("\n".join(json.dumps(entry) for entry in entries), encoding="utf-8")

    from scripts.report_accuracy_metrics import load_events, write_report

    events = load_events(limit=3)
    assert len(events) == 3
    write_report(events)
    content = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "accuracy guard" not in content.lower()
    assert "Total evaluations" in content
