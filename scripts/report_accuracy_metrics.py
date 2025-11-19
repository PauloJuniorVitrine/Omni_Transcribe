from __future__ import annotations

import json
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Deque, List, Optional

METRICS_PATH = Path("logs/metrics.log")
OUTPUT_PATH = Path("docs/accuracy_metrics_summary.md")
MAX_EVENTS = 2000


@dataclass
class AccuracyEvent:
    job_id: str
    score: float
    requires_review: bool
    baseline: float
    wer: float
    timestamp: str


def load_events(limit: Optional[int] = MAX_EVENTS) -> List[AccuracyEvent]:
    if not METRICS_PATH.exists():
        return []
    buffer: Deque[AccuracyEvent] = deque(maxlen=limit or None)
    with METRICS_PATH.open("r", encoding="utf-8") as cursor:
        for raw_line in cursor:
            line = raw_line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("event") != "accuracy.guard.evaluated":
                continue
            body = payload.get("payload") or {}
            try:
                event = AccuracyEvent(
                    job_id=str(body.get("job_id")),
                    score=float(body.get("score", 0)),
                    requires_review=bool(body.get("requires_review")),
                    baseline=float(body.get("baseline", 0)),
                    wer=float(body.get("wer_active", 0)),
                    timestamp=payload.get("timestamp", ""),
                )
            except (TypeError, ValueError):
                continue
            buffer.append(event)
    return list(buffer)


def write_report(events: List[AccuracyEvent]) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat()
    if not events:
        OUTPUT_PATH.write_text(
            f"# Accuracy Metrics\n\nNenhum evento registrado ate {timestamp}.\n", encoding="utf-8"
        )
        return
    avg_score = mean(event.score for event in events)
    avg_wer = mean(event.wer for event in events)
    flagged = sum(1 for event in events if event.requires_review)
    lines = [
        "# Accuracy Metrics",
        "",
        f"- Generated at: {timestamp}",
        f"- Total evaluations: {len(events)}",
        f"- Average score: {avg_score:.4f}",
        f"- Average WER: {avg_wer:.4f}",
        f"- Jobs marked for review: {flagged}",
        "",
        "| Job ID | Score | WER | Requires Review | Timestamp |",
        "| --- | --- | --- | --- | --- |",
    ]
    for event in events[-20:]:
        lines.append(
            f"| {event.job_id} | {event.score:.4f} | {event.wer:.4f} | {'✅' if not event.requires_review else '⚠️'} | {event.timestamp} |"
        )
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    events = load_events()
    write_report(events)


if __name__ == "__main__":
    main()
