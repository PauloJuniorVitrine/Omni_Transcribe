#!/usr/bin/env python
from __future__ import annotations

import os
import textwrap
import sys

from config.runtime_credentials import RuntimeCredentialStore, DEFAULT_CREDENTIALS


def main() -> None:
    secret = os.environ.get("CREDENTIALS_SECRET_KEY")
    if not secret:
        sys.exit("CREDENTIALS_SECRET_KEY is required to generate the runtime credentials.")

    store = RuntimeCredentialStore()
    store.save(DEFAULT_CREDENTIALS)

    message = textwrap.dedent(
        f"""
        ✅ Runtime credential store generated at: {store.path}
        - Secret key used (first 6 chars): {secret[:6]}…
        - Push `config/runtime_credentials.json` only if the contents are valid for your environment.
        """
    )
    print(message.strip())


if __name__ == "__main__":
    main()
