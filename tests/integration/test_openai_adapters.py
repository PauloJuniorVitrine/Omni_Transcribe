from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
import requests
from requests.models import Response

from infrastructure.api.openai_client import OpenAIChatHttpClient, OpenAIWhisperHttpClient


class DummyResponse(Response):
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        super().__init__()
        self._content = json.dumps(payload).encode("utf-8")
        self.status_code = status_code


def test_openai_whisper_client_builds_request(monkeypatch, tmp_path: Path):
    captured = {}

    def fake_post(url, headers, data, files, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        captured["filename"] = files["file"][0]
        return DummyResponse(
            {
                "text": "hello world",
                "language": "en",
                "duration": 12.3,
                "segments": [{"id": 0, "start": 0.0, "end": 1.0, "text": "hello"}],
            }
        )

    monkeypatch.setattr(requests, "post", fake_post)

    audio_file = tmp_path / "sample.wav"
    audio_file.write_bytes(b"\x00\x01")

    client = OpenAIWhisperHttpClient(api_key="key", base_url="https://api.test", model="gpt-4o-transcribe")
    result = client.transcribe(file_path=audio_file, language="pt", task="translate")

    assert captured["url"].endswith("/audio/transcriptions")
    assert captured["headers"]["Authorization"] == "Bearer key"
    assert captured["data"]["language"] == "pt"
    assert captured["data"]["task"] == "translate"
    assert captured["filename"] == "sample.wav"
    assert result["language"] == "en"
    assert result["segments"][0]["text"] == "hello"


def test_openai_chat_client_builds_payload(monkeypatch):
    captured = {}

    def fake_post(url, headers, data, timeout):
        captured["url"] = url
        captured["payload"] = json.loads(data)
        return DummyResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps({"text": "OK"}),
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr(requests, "post", fake_post)

    client = OpenAIChatHttpClient(api_key="key", base_url="https://api.test", model="gpt-4.1")
    response = client.complete(system_prompt="sys", user_prompt="user", response_format="json_object")

    assert captured["url"].endswith("/chat/completions")
    assert captured["payload"]["model"] == "gpt-4.1"
    assert captured["payload"]["messages"][0]["content"] == "sys"
    assert response == json.dumps({"text": "OK"})
