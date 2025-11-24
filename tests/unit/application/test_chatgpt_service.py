from __future__ import annotations

import json

from application.services.chatgpt_service import ChatGptPostEditingService
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import Segment, TranscriptionResult


class StubChatClient:
    def __init__(self) -> None:
        self.last_request: tuple[str, str] | None = None

    def complete(self, *, system_prompt: str, user_prompt: str, response_format: str = "json_object") -> str:
        self.last_request = (system_prompt, user_prompt)
        payload = {
            "text": "Contact me at email@example.com",
            "segments": [
                {"id": 0, "start": 0.0, "end": 1.0, "text": "Call me at 11 91234-5678"},
            ],
            "flags": [{"type": "note", "message": "ok"}],
            "language": "pt",
        }
        return json.dumps(payload)


def test_chatgpt_service_applies_profile_rules_and_masks_pii(tmp_path) -> None:
    profile = Profile(
        id="geral",
        meta={
            "disclaimers": ["Use apenas como apoio"],
            "post_edit": {"anonymize_pii": True},
            "instructions": ["normalize punctuation"],
        },
        prompt_body="ajuste o texto",
    )
    job = Job(id="job1", source_path=tmp_path / "audio.wav", profile_id="geral")
    transcription = TranscriptionResult(
        text="Meu email é email@example.com",
        segments=[Segment(id=0, start=0.0, end=1.0, text="Use 11 91234-5678")],
        language="pt",
        duration_sec=1.0,
        engine="openai",
        metadata={},
    )

    client = StubChatClient()
    service = ChatGptPostEditingService(client)
    result = service.run(job, profile, transcription)

    assert result.text == "Contact me at [email]"
    assert result.segments[0].text == "Call me at [phone]"
    assert result.flags == [{"type": "note", "message": "ok"}]
    system_prompt, user_prompt = client.last_request
    assert "Use apenas como apoio" in system_prompt
    payload = json.loads(user_prompt)
    assert payload["profile_meta"]["post_edit"]["anonymize_pii"] is True
    assert payload["transcription"]["text"] == transcription.text


def test_chatgpt_service_uses_transcription_segments_when_missing_payload(tmp_path) -> None:
    class EmptySegmentsClient(StubChatClient):
        def complete(self, *, system_prompt: str, user_prompt: str, response_format: str = "json_object") -> str:
            self.last_request = (system_prompt, user_prompt)
            return json.dumps({"text": "kept"})

    profile = Profile(id="geral", meta={}, prompt_body="body")
    transcription = TranscriptionResult(
        text="Original text",
        segments=[Segment(id=7, start=1.0, end=2.5, text="segment text")],
        language="en",
        duration_sec=2.5,
        engine="openai",
        metadata={},
    )
    job = Job(id="job2", source_path=tmp_path / "audio.wav", profile_id="geral")

    client = EmptySegmentsClient()
    service = ChatGptPostEditingService(client)

    result = service.run(job, profile, transcription)

    assert result.text == "kept"
    assert len(result.segments) == 1
    assert result.segments[0].id == 7
    assert result.segments[0].text == "segment text"
