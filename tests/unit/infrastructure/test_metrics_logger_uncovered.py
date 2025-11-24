from __future__ import annotations

from infrastructure.telemetry import metrics_logger


def test_record_metric_writes_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(metrics_logger, "METRICS_PATH", tmp_path / "metrics.log")
    monkeypatch.setattr(metrics_logger, "_post_webhooks", lambda urls, payload: None)

    metrics_logger.record_metric("event", {"a": 1})

    assert metrics_logger.METRICS_PATH.exists()


def test_notify_alert_writes_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(metrics_logger, "ALERTS_PATH", tmp_path / "alerts.log")
    monkeypatch.setattr(metrics_logger, "_post_webhooks", lambda urls, payload: None)

    metrics_logger.notify_alert("alert", {"a": 1})

    assert metrics_logger.ALERTS_PATH.exists()
