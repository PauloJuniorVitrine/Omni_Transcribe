from __future__ import annotations

import re

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\d{2}[-.\s]?)?\d{4,5}[-.\s]?\d{4}\b")
CPF_RE = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")


def mask_text(text: str) -> str:
    """Simple PII masking helper used when profiles demand anonymization."""
    masked = EMAIL_RE.sub("[email]", text)
    masked = PHONE_RE.sub("[phone]", masked)
    masked = CPF_RE.sub("[cpf]", masked)
    return masked
