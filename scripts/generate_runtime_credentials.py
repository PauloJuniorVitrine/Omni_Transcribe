#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import textwrap

from config.runtime_credentials import DEFAULT_CREDENTIALS, RuntimeCredentialStore


def main() -> None:
    secret = os.environ.get("CREDENTIALS_SECRET_KEY")
    if not secret:
        sys.exit("CREDENTIALS_SECRET_KEY precisa estar configurada no ambiente.")

    store = RuntimeCredentialStore()
    store.save(DEFAULT_CREDENTIALS)

    print(
        textwrap.dedent(
            f"""
            ✅ Cofre de credenciais gerado: {store.path}
            🔐 Usando chave (6 primeiros chars): {secret[:6]}
            ⚠️ Não compartilhe essa chave; mantenha o arquivo fora do git ou regenere quando trocar a chave.
            """
        ).strip()
    )


if __name__ == "__main__":
    main()
