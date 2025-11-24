from __future__ import annotations

import json
from pathlib import Path

from application.services.chatgpt_service import ChatGptPostEditingService
from application.services.retry import RetryExecutor
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import Segment, TranscriptionResult
from domain.entities.value_objects import EngineType


class _DummyClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls = 0

    def complete(self, system_prompt: str, user_prompt: str, response_format: str) -> str:
        self.calls += 1
        # echo prompts for coverage
        assert "Disclaimers" in system_prompt or "Disclaimers" in system_prompt
        assert response_format == "json_object"
        json.loads(user_prompt)
        return json.dumps(self.payload)


class _EchoRetry(RetryExecutor[str]):
    def __init__(self) -> None:
        super().__init__()

    def run(self, func):  # type: ignore[override]
        return func()


def _transcription() -> TranscriptionResult:
    return TranscriptionResult(
        text="Olá mundo",
        segments=[Segment(id=1, start=0.0, end=1.0, text="email me at foo@bar.com", speaker=None)],
        language="pt",
        duration_sec=1.0,
        engine=EngineType.OPENAI.value,
        metadata={},
    )


def test_run_masks_pii_when_profile_requests() -> None:
    profile = Profile(
        id="p1",
        meta={"post_edit": {"anonymize_pii": True}},
        prompt_body="body",
        disclaimers=["keep private"],
    )
    client = _DummyClient({"text": "call me at 9999-0000", "segments": []})
    service = ChatGptPostEditingService(client, retry_executor=_EchoRetry())
    job = Job(id="j1", source_path=Path("a.wav"), profile_id="p1")

    result = service.run(job, profile, _transcription())

    assert "[phone]" in result.text
    assert result.flags == []
    assert result.segments[0].text  # present


def test_run_falls_back_to_transcription_segments_when_missing() -> None:
    profile = Profile(id="p2", meta={}, prompt_body="")
    client = _DummyClient({"text": "ok", "flags": ["f1"]})
    service = ChatGptPostEditingService(client, retry_executor=_EchoRetry())
    job = Job(id="j2", source_path=Path("a.wav"), profile_id="p2")
    transcription = _transcription()

    result = service.run(job, profile, transcription)

    assert result.text == "ok"
    assert len(result.segments) == len(transcription.segments)
    assert result.flags == ["f1"]
