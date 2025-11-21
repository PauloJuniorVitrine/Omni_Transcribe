#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import sys
import textwrap
from pathlib import Path


REQUIRED_ENV = {
    "OPENAI_API_KEY": "Chave da OpenAI utilizada pelo engine `openai`.",
    "CREDENTIALS_SECRET_KEY": "Segredo mestre (ou defina RUNTIME_CREDENTIALS_KEY).",
}


def _confirm_env(key: str) -> bool:
    value = os.getenv(key)
    if not value:
        return False
    return bool(value.strip())


def _has_fallback_secret_file() -> bool:
    return Path("config/.credentials_secret.key").exists()


def _alert(msg: str) -> None:
    print(msg, file=sys.stderr)


def main() -> int:
    engine = os.getenv("ASR_ENGINE", "openai").lower()
    missing = []
    hints: list[str] = []

    if engine == "openai":
        if not _confirm_env("OPENAI_API_KEY"):
            missing.append("OPENAI_API_KEY")
        else:
            hints.append("OPENAI_API_KEY definida via variavel de ambiente.")
    else:
        ffmpeg = shutil.which("ffmpeg") or shutil.which("avconv")
        if ffmpeg:
            hints.append(f"Engine local configurado; encontrou {Path(ffmpeg).name}.")
        else:
            _alert("Warning: `ASR_ENGINE=local` requer `ffmpeg` ou `avconv` no `PATH`.")

    if not (_confirm_env("CREDENTIALS_SECRET_KEY") or _confirm_env("RUNTIME_CREDENTIALS_KEY")):
        if _has_fallback_secret_file():
            hints.append("Segredo local `config/.credentials_secret.key` detectado.")
        else:
            missing.append("CREDENTIALS_SECRET_KEY / RUNTIME_CREDENTIALS_KEY")
    else:
        hints.append("Segredo criptografico em variaveis de ambiente detectado.")

    if missing:
        _alert("Pre-requisitos ausentes:")
        for key in missing:
            description = REQUIRED_ENV.get(key, "Variavel necessaria.")
            _alert(f"  - {key}: {description}")
        _alert(
            textwrap.dedent(
                """
                Exemplo (PowerShell):
                    $env:OPENAI_API_KEY = 'sk-...'
                    $env:CREDENTIALS_SECRET_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
                    .\\TranscribeFlow.exe
                """
            ).strip()
        )
        return 1

    print("Pre-requisitos validados com sucesso.")
    for hint in hints:
        print(f"   {hint}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
