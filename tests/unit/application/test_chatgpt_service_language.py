from __future__ import annotations

import json

from application.services.chatgpt_service import ChatGptPostEditingService
from domain.entities.job import Job
from domain.entities.profile import Profile
from domain.entities.transcription import Segment, TranscriptionResult


class _Client:
    def complete(self, *, system_prompt: str, user_prompt: str, response_format: str = "json_object") -> str:
        payload = {"text": "hi there", "segments": [{"id": 0, "start": 0, "end": 1, "text": "hi"}]}
        return json.dumps(payload)


def test_chatgpt_service_defaults_language_and_flags(tmp_path) -> None:
    profile = Profile(id="p", meta={}, prompt_body="body")
    job = Job(id="job", source_path=tmp_path / "a.wav", profile_id="p")
    transcription = TranscriptionResult(
        text="source", segments=[Segment(id=5, start=1, end=2, text="seg")], language="fr", metadata={}
    )
    service = ChatGptPostEditingService(_Client())

    result = service.run(job, profile, transcription)

    assert result.language == "fr"
    assert result.flags == []
