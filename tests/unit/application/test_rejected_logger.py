from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

from application.services.rejected_logger import FilesystemRejectedLogger
from domain.entities.job import Job
from domain.entities.value_objects import EngineType, JobStatus


def test_rejected_logger_writes_payload(tmp_path):
    logger = FilesystemRejectedLogger(tmp_path / "rejected")
    audio = tmp_path / "a.wav"
    audio.write_text("a", encoding="utf-8")
    job = Job(id="j1", source_path=audio, profile_id="p", engine=EngineType.OPENAI, status=JobStatus.REJECTED)

    path = logger.record(job, error="boom", stage="post_edit", payload={"foo": "bar"})

    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["job_id"] == "j1"
    assert data["error"] == "boom"
    assert data["payload"]["foo"] == "bar"
    # timestamp format keeps date
    datetime.fromisoformat(data["timestamp_utc"])
