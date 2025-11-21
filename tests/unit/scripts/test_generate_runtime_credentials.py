import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def _call_generator(output: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/generate_runtime_credentials.py", "--output", str(output)],
        env=env,
        check=True,
        capture_output=True,
    )


def test_generator_creates_encrypted_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TEST_MODE", "0")
    secret = "A" * 32
    env = os.environ.copy()
    env["CREDENTIALS_SECRET_KEY"] = secret
    target = tmp_path / "runtime_credentials.json"
    _call_generator(target, env)
    assert target.exists()
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload.get("encrypted") is True
    assert "payload" in payload


def test_generator_requires_secret(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("CREDENTIALS_SECRET_KEY", None)
    target = tmp_path / "runtime_credentials.json"
    with pytest.raises(subprocess.CalledProcessError):
        _call_generator(target, env)
