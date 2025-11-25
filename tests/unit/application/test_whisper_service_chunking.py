from __future__ import annotations

import os
from pathlib import Path

import pytest

from application.services.audio_chunker import AudioChunk
from application.services.whisper_service import WhisperService
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.value_objects import EngineType


class _StubChunker:
    def __init__(self, chunks: list[AudioChunk]) -> None:
        self._chunks = chunks

    def split(self, file_path: Path) -> list[AudioChunk]:
        return self._chunks


class _StubAsrClient:
    def __init__(self) -> None:
        self.calls: list[Path] = []

    def transcribe(
        self,
        *,
        file_path: Path,
        language: str | None,
        task: str,
        response_format: str | None = None,
        chunking_strategy: str | None = None,
    ):
        self.calls.append(file_path)
        idx = len(self.calls) - 1
        return {
            "text": f"chunk-{idx}",
            "segments": [{"id": idx, "start": 0.0, "end": 1.0, "text": f"seg-{idx}"}],
            "language": "pt",
            "duration": 1.0,
        }


def test_whisper_service_chunking_adjusts_segments_and_cleans_chunks(tmp_path):
    source = tmp_path / "audio.wav"
    source.write_bytes(b"x" * (1024 * 1024 + 10))  # >1MB to trigger custom guard

    chunk_a = AudioChunk(path=tmp_path / "c1.wav", start_sec=0.0, duration_sec=1.0)
    chunk_b = AudioChunk(path=tmp_path / "c2.wav", start_sec=2.0, duration_sec=1.0)
    chunk_a.path.write_text("a", encoding="utf-8")
    chunk_b.path.write_text("b", encoding="utf-8")

    stub_client = _StubAsrClient()
    chunker = _StubChunker([chunk_a, chunk_b])
    service = WhisperService(
        engine_clients={"openai": stub_client},
        chunker=chunker,
        chunk_trigger_mb=1,  # small threshold for test
    )
    # force chunking regardless of size check outcome
    service._should_chunk = lambda _fp: True  # type: ignore[assignment]

    job = Job(id="j1", source_path=source, profile_id="p", engine=EngineType.OPENAI)
    profile = Profile(id="p", meta={}, prompt_body="x")

    result = service.run(job, profile, task="transcribe")

    assert result.text == "chunk-0 chunk-1"
    assert len(result.segments) == 2
    assert result.segments[1].start == pytest.approx(2.0)
    assert result.metadata.get("chunked") is True
    # temp chunk files removed
    assert not chunk_a.path.exists()
    assert not chunk_b.path.exists()
