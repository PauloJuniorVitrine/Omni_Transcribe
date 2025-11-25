from __future__ import annotations

import json

from domain.entities.transcription import Segment, TranscriptionResult
from application.services.chatgpt_service import ChatGptPostEditingService


def _make_transcription() -> TranscriptionResult:
    segments = [Segment(id=0, start=0.0, end=1.0, text="original", speaker="spk1")]
    return TranscriptionResult(text="original", segments=segments, language="pt", metadata={})


def test_safe_parse_payload_handles_invalid_json():
    transcription = _make_transcription()
    result = ChatGptPostEditingService._safe_parse_payload("not-json", transcription)
    assert result["text"] == transcription.text
    assert isinstance(result["segments"], list)
    assert result["flags"] == []


def test_safe_parse_payload_handles_non_dict_payload():
    transcription = _make_transcription()
    result = ChatGptPostEditingService._safe_parse_payload(json.dumps([1, 2, 3]), transcription)
    assert result["text"] == transcription.text
    assert isinstance(result["segments"], list)


def test_safe_parse_payload_returns_segments_only_if_list():
    transcription = _make_transcription()
    payload = json.dumps({"text": "ok", "segments": {"a": 1}, "flags": "bad"})
    result = ChatGptPostEditingService._safe_parse_payload(payload, transcription)
    assert result["text"] == "ok"
    assert isinstance(result["segments"], list)
    assert result["flags"] == []
