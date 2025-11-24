from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

import pytest

from application.services.audio_chunker import AudioChunk
from application.services.whisper_service import WhisperService
from application.services.retry import RetryExecutor
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import TranscriptionResult
from domain.entities.value_objects import EngineType


class _SimpleRetry(RetryExecutor[Dict]):
    def run(self, func):  # type: ignore[override]
        return func()


class _FakeClient:
    def __init__(self, response: Dict) -> None:
        self.response = response
        self.calls: List[Path] = []

    def transcribe(self, *, file_path: Path, language: str | None, task: str) -> Dict:
        self.calls.append(file_path)
        return dict(self.response)


def _job(tmp_path: Path) -> Job:
    wav = tmp_path / "audio.wav"
    wav.write_bytes(b"data")
    return Job(id="j", source_path=wav, profile_id="p", engine=EngineType.OPENAI)


def test_should_chunk_handles_stat_error(monkeypatch, tmp_path: Path) -> None:
    service = WhisperService(engine_clients={}, chunker=None)
    missing = tmp_path / "missing.wav"
    assert service._should_chunk(missing) is False


def test_run_raises_when_engine_missing(tmp_path: Path) -> None:
    service = WhisperService(engine_clients={}, chunker=None)
    job = _job(tmp_path)
    profile = Profile(id="p", meta={}, prompt_body="")
    with pytest.raises(ValueError):
        service.run(job, profile)


def test_run_single_builds_result(monkeypatch, tmp_path: Path) -> None:
    client = _FakeClient({"text": "ok", "segments": [{"start": 0, "end": 1, "text": "hi"}], "language": "en"})
    service = WhisperService(engine_clients={EngineType.OPENAI.value: client}, retry_executor=_SimpleRetry(), chunker=None)
    job = _job(tmp_path)
    profile = Profile(id="p", meta={}, prompt_body="")

    result = service.run(job, profile)

    assert result.text == "ok"
    assert result.language == "en"
    assert result.segments[0].text == "hi"


def test_run_chunked_adjusts_segments_and_cleans(monkeypatch, tmp_path: Path) -> None:
    chunk_paths = []

    def _chunker_split(_path: Path) -> List[AudioChunk]:
        paths = []
        for idx in range(2):
            p = tmp_path / f"chunk{idx}.wav"
            p.write_bytes(b"c")
            paths.append(p)
            chunk_paths.append(p)
        return [
            AudioChunk(path=paths[0], start_sec=0.0, duration_sec=1.0),
            AudioChunk(path=paths[1], start_sec=1.0, duration_sec=1.0),
        ]

    client = _FakeClient(
        {
            "text": "part",
            "segments": [{"start": 0.0, "end": 1.0, "text": "seg"}],
            "language": "en",
            "duration": 1.0,
        }
    )
    job = _job(tmp_path)
    profile = Profile(id="p", meta={}, prompt_body="")
    service = WhisperService(
        engine_clients={EngineType.OPENAI.value: client},
        retry_executor=_SimpleRetry(),
        chunker=type("Chunker", (), {"split": staticmethod(_chunker_split)}),
        chunk_trigger_mb=0,
    )
    monkeypatch.setattr(service, "_should_chunk", lambda _path: True)

    result = service.run(job, profile)

    assert result.metadata["chunked"] is True
    assert len(result.segments) == 2  # adjusted segments
    assert all(not p.exists() for p in chunk_paths)
