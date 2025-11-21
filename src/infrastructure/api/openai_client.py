from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import requests

from application.services.ports import AsrEngineClient, ChatModelClient


class OpenAIWhisperHttpClient(AsrEngineClient):
    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4o-transcribe", timeout: int = 600) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def transcribe(self, *, file_path: Path, language: str | None, task: str) -> Dict[str, Any]:
        url = f"{self.base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        data = {"model": self.model, "response_format": "verbose_json", "task": task}
        if language:
            data["language"] = language
        with file_path.open("rb") as fp:
            files = {"file": (file_path.name, fp, "application/octet-stream")}
            response = requests.post(url, headers=headers, data=data, files=files, timeout=self.timeout)
        response.raise_for_status()
        return response.json()


class OpenAIChatHttpClient(ChatModelClient):
    def __init__(self, api_key: str, base_url: str, model: str = "gpt-4.1-mini", timeout: int = 120) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def complete(self, *, system_prompt: str, user_prompt: str, response_format: str = "json_object") -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": response_format},
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=self.timeout)
        response.raise_for_status()
        body = response.json()
        choices: List[Dict[str, Any]] = body.get("choices", [])
        if not choices:
            raise RuntimeError("Resposta da API OpenAI nao contem choices.")
        return choices[0]["message"]["content"]
