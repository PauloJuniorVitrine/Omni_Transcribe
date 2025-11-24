from __future__ import annotations

import pytest

from infrastructure.api.openai_client import OpenAIChatHttpClient


class _Resp:
    def __init__(self, body: dict) -> None:
        self._body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


def test_complete_raises_when_no_choices(monkeypatch):
    def _post(url, headers=None, data=None, timeout=None):
        return _Resp({"choices": []})

    client = OpenAIChatHttpClient(api_key="k", base_url="http://x")
    monkeypatch.setattr("infrastructure.api.openai_client.requests.post", _post)

    with pytest.raises(RuntimeError):
        client.complete(system_prompt="sys", user_prompt="user", response_format="json_object")
