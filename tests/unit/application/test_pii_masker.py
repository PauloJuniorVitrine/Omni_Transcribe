from __future__ import annotations

from application.services.pii import mask_text


def test_mask_text_replaces_email_phone_cpf():
    text = "Contato: ana@example.com, Tel +55 11 99999-8888, CPF 123.456.789-01"
    masked = mask_text(text)
    assert "[email]" in masked
    assert "[phone]" in masked
    assert "[cpf]" in masked


def test_mask_text_idempotent_on_clean_text():
    clean = "Sem dados sensiveis aqui."
    masked = mask_text(clean)
    assert masked == clean
