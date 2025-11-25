from __future__ import annotations

from pathlib import Path

from application.services.whisper_service import WhisperService
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.value_objects import EngineType


class _Client:
    def transcribe(
        self,
        *,
        file_path: Path,
        language: str | None,
        task: str,
        response_format: str | None = None,
        chunking_strategy: str | None = None,
    ):
        return {"text": "ok", "segments": [], "language": None, "duration": None}


def test_whisper_service_build_result_defaults_language(tmp_path) -> None:
    audio = tmp_path / "a.wav"
    audio.write_bytes(b"x")
    job = Job(id="j", source_path=audio, profile_id="p", engine=EngineType.OPENAI)
    profile = Profile(id="p", meta={}, prompt_body="body")

    service = WhisperService({"openai": _Client()}, default_language="auto", chunk_trigger_mb=0)
    result = service.run(job, profile, task="transcribe")

    assert result.language == "auto"
    assert result.metadata["task"] == "transcribe"
