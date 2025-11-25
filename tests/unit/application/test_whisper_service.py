from __future__ import annotations

from pathlib import Path

import pytest

from application.services.audio_chunker import AudioChunk
from application.services.whisper_service import WhisperService
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.value_objects import EngineType


class StubAsrClient:
    def __init__(self, responses: list[dict] | None = None) -> None:
        self.calls: list[tuple[Path, str | None, str]] = []
        self.responses = responses or [
            {
                "text": " cleaned ",
                "segments": [
                    {"id": 1, "start": 0.0, "end": 1.5, "text": " hi "},
                    {"start": 1.5, "end": 3.0, "text": " there"},
                ],
                "language": "pt",
                "duration": 180.0,
            }
        ]

    def transcribe(
        self,
        *,
        file_path: Path,
        language: str | None,
        task: str,
        response_format: str | None = None,
        chunking_strategy: str | None = None,
    ):
        self.calls.append((file_path, language, task))
        idx = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[idx]


def test_whisper_service_calls_engine_and_maps_segments(tmp_path: Path) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"x")

    job = Job(id="job1", source_path=audio, profile_id="geral", engine=EngineType.OPENAI)
    profile = Profile(id="geral", meta={"language": "auto"}, prompt_body="body")

    client = StubAsrClient()
    service = WhisperService({"openai": client})

    result = service.run(job, profile, task="transcribe")

    assert client.calls == [(audio, None, "transcribe")]
    assert result.text == " cleaned "
    assert len(result.segments) == 2
    assert result.segments[0].id == 1
    assert result.segments[0].text == "hi"
    assert result.segments[1].id == 1  # default enumerated id
    assert result.language == "pt"
    assert result.duration_sec == 180.0
    assert result.metadata["engine"] == "openai"


def test_whisper_service_errors_without_client(tmp_path: Path) -> None:
    job = Job(id="job1", source_path=tmp_path / "file.wav", profile_id="geral", engine=EngineType.LOCAL)
    profile = Profile(id="geral", meta={}, prompt_body="body")
    service = WhisperService({"openai": StubAsrClient()})

    with pytest.raises(ValueError, match="Nenhum cliente configurado"):
        service.run(job, profile)


class StubChunker:
    def __init__(self, chunks):
        self._chunks = chunks

    def split(self, file_path: Path):
        return self._chunks


def test_whisper_service_chunks_large_file(tmp_path: Path) -> None:
    audio = tmp_path / "audio_long.wav"
    audio.write_bytes(b"x" * (2 * 1024 * 1024))

    chunk1 = tmp_path / "chunk1.wav"
    chunk1.write_bytes(b"a")
    chunk2 = tmp_path / "chunk2.wav"
    chunk2.write_bytes(b"b")

    chunker = StubChunker(
        [
            AudioChunk(path=chunk1, start_sec=0.0, duration_sec=5.0),
            AudioChunk(path=chunk2, start_sec=5.0, duration_sec=5.0),
        ]
    )

    responses = [
        {
            "text": "hello",
            "segments": [{"id": 0, "start": 0.0, "end": 2.0, "text": "hello"}],
            "language": "pt",
            "duration": 5.0,
        },
        {
            "text": "world",
            "segments": [{"id": 1, "start": 0.0, "end": 3.0, "text": "world"}],
            "language": "pt",
            "duration": 5.0,
        },
    ]
    client = StubAsrClient(responses=responses)
    service = WhisperService({"openai": client}, chunker=chunker, chunk_trigger_mb=1)

    job = Job(id="job-chunk", source_path=audio, profile_id="geral", engine=EngineType.OPENAI)
    profile = Profile(id="geral", meta={}, prompt_body="body")

    result = service.run(job, profile)

    assert result.text == "hello world"
    assert len(result.segments) == 2
    assert pytest.approx(result.segments[1].start, rel=1e-3) == 5.0
    assert result.metadata["chunked"] is True


def test_whisper_service_handles_stat_error_without_chunking(monkeypatch, tmp_path: Path) -> None:
    audio = tmp_path / "missing.wav"  # file will not be created
    job = Job(id="job3", source_path=audio, profile_id="geral", engine=EngineType.OPENAI)
    profile = Profile(id="geral", meta={}, prompt_body="body")

    class _Client(StubAsrClient):
        def transcribe(
            self,
            *,
            file_path: Path,
            language: str | None,
            task: str,
            response_format: str | None = None,
            chunking_strategy: str | None = None,
        ):
            return {
                "text": "ok",
                "segments": [],
                "language": "en",
                "duration": 1.0,
            }

    client = _Client()

    # chunker provided, but stat will raise and _should_chunk must return False
    class _Chunker:
        def split(self, file_path: Path):
            raise AssertionError("Should not chunk when stat fails")

    def _stat_raises(self, follow_symlinks=True):
        raise OSError("stat failed")

    monkeypatch.setattr(Path, "stat", _stat_raises, raising=False)
    service = WhisperService({"openai": client}, chunker=_Chunker(), chunk_trigger_mb=1)

    result = service.run(job, profile)

    assert result.text == "ok"
