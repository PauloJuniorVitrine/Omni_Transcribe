from __future__ import annotations

import statistics
import time
from pathlib import Path

import pytest

from application.services.whisper_service import WhisperService
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import Segment, TranscriptionResult
from domain.entities.value_objects import EngineType


class _StubClient:
    def transcribe(self, *, file_path: Path, language: str | None, task: str):
        return {
            "text": "ok",
            "segments": [{"id": 0, "start": 0.0, "end": 1.0, "text": "ok"}],
            "language": "en",
            "duration": 1.0,
        }


def _make_job(tmp_path: Path) -> Job:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"x")
    return Job(id="job-load", source_path=audio, profile_id="geral", engine=EngineType.OPENAI)


def _patch_perf_counter(monkeypatch: pytest.MonkeyPatch, step: float) -> None:
    tick = {"value": 0.0}

    def fake_perf_counter() -> float:
        tick["value"] += step
        return tick["value"]

    monkeypatch.setattr(time, "perf_counter", fake_perf_counter)


def test_whisper_pipeline_multiple_runs_under_threshold(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_perf_counter(monkeypatch, step=0.01)
    job = _make_job(tmp_path)
    profile = Profile(id="geral", meta={}, prompt_body="body")
    service = WhisperService({"openai": _StubClient()}, chunk_trigger_mb=0)

    durations = []
    for _ in range(20):
        start = time.perf_counter()
        result = service.run(job, profile, task="transcribe")
        durations.append(time.perf_counter() - start)
        assert result.text == "ok"
    p95 = statistics.quantiles(sorted(durations), n=20)[-1]
    assert p95 < 0.5


def test_post_edit_and_artifact_stub_under_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_perf_counter(monkeypatch, step=0.02)

    def fake_post_edit(job, profile, transcription):
        return TranscriptionResult(
            text=transcription.text,
            segments=[Segment(id=1, start=0.0, end=1.0, text="x")],
            language=transcription.language,
            metadata={},
        )

    start = time.perf_counter()
    transcription = TranscriptionResult(text="ok", segments=[], language="en", metadata={})
    post_edit = fake_post_edit(None, None, transcription)
    duration = time.perf_counter() - start
    assert post_edit.text == "ok"
    assert duration < 0.5
