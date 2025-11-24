from __future__ import annotations

import json
import pytest

from infrastructure.api.gotranscript_client import GoTranscriptClient
from infrastructure.api.openai_client import OpenAIChatHttpClient


def test_gotranscript_client_requires_api_key(tmp_path) -> None:
    with pytest.raises(ValueError):
        GoTranscriptClient(base_url="https://api", api_key="")


def test_openai_client_raises_when_no_choices(monkeypatch) -> None:
    client = OpenAIChatHttpClient(api_key="k", base_url="https://api", model="m")

    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": []}

    def _post(url, headers=None, data=None, timeout=None):
        return _Resp()

    monkeypatch.setattr("infrastructure.api.openai_client.requests.post", _post)
    with pytest.raises(RuntimeError):
        client.complete(system_prompt="s", user_prompt="u")
