#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config.runtime_credentials import DEFAULT_CREDENTIALS, RuntimeCredentialStore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera runtime credentials criptografadas.")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="config/runtime_credentials.json",
        help="Caminho do arquivo de credenciais gerado.",
    )
    return parser.parse_args()


def create_runtime_store(output_path: str) -> RuntimeCredentialStore:
    from pathlib import Path

    path = Path(output_path)
    return RuntimeCredentialStore(path=path)


def main() -> None:
    args = parse_args()
    secret = os.environ.get("CREDENTIALS_SECRET_KEY")
    if not secret:
        sys.exit("CREDENTIALS_SECRET_KEY precisa estar configurada no ambiente.")

    store = create_runtime_store(args.output)
    store.save(DEFAULT_CREDENTIALS)

    print(
        textwrap.dedent(
            f"""
            Cofre de credenciais gerado: {store.path}
            Usando chave (6 primeiros chars): {secret[:6]}
            Não compartilhe essa chave; mantenha o arquivo fora do git ou regenere quando trocar a chave.
            """
        ).strip()
    )


if __name__ == "__main__":
    main()
