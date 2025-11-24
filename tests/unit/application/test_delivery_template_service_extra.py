from __future__ import annotations

from pathlib import Path

import pytest

from application.services.delivery_template_service import DeliveryTemplateRegistry


def _write_template(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_template_without_id_uses_filename(tmp_path: Path) -> None:
    template_path = tmp_path / "noid.template.txt"
    _write_template(template_path, "Body sem front matter")
    registry = DeliveryTemplateRegistry(tmp_path)

    doc = registry.get("noid")

    assert doc.id == "noid"
    assert doc.body == "Body sem front matter"


def test_missing_template_falls_back_to_default(tmp_path: Path) -> None:
    default_path = tmp_path / "default.template.txt"
    _write_template(default_path, "---\nid: default\nname: padrao\n---\n{{transcript}}")
    registry = DeliveryTemplateRegistry(tmp_path)

    doc = registry.get("inexistente")

    assert doc.id == "default"
    assert "transcript" in doc.body


def test_localized_template_loaded_lazily(tmp_path: Path) -> None:
    pt_dir = tmp_path / "pt-br"
    localized_path = pt_dir / "custom.template.txt"
    _write_template(localized_path, "---\nid: custom\nlocale: pt-BR\n---\n{{transcript}} PT")
    registry = DeliveryTemplateRegistry(tmp_path)

    rendered = registry.render("custom", {"transcript": "oi"}, language="pt-BR")

    assert "oi" in rendered
    doc = registry.get("custom")
    assert doc.id == "custom"
    assert doc.locale == "pt-br"


def test_split_front_matter_handles_plain_text(tmp_path: Path) -> None:
    template_path = tmp_path / "plain.template.txt"
    _write_template(template_path, "sem yaml aqui")
    registry = DeliveryTemplateRegistry(tmp_path)

    doc = registry.get("plain")

    assert doc.description == ""
    assert doc.body == "sem yaml aqui"


def test_default_template_id_returns_default_when_no_files(tmp_path: Path) -> None:
    registry = DeliveryTemplateRegistry(tmp_path)
    assert registry.default_template_id == "default"


def test_infer_locale_returns_none_for_outside_path(tmp_path: Path) -> None:
    registry = DeliveryTemplateRegistry(tmp_path)
    other = tmp_path.parent / "other" / "custom.template.txt"
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_text("---\nid: custom\n---\nbody", encoding="utf-8")
    assert registry._infer_locale_from_path(other) is None  # type: ignore[attr-defined]


def test_get_localized_returns_none_for_missing_language(tmp_path: Path) -> None:
    registry = DeliveryTemplateRegistry(tmp_path)
    # sem language
    assert registry._get_localized("id", None) is None  # type: ignore[attr-defined]
    # language vazia
    assert registry._get_localized("id", "") is None  # type: ignore[attr-defined]
    # language sem template correspondente
    assert registry._get_localized("id", "fr-FR") is None  # type: ignore[attr-defined]


def test_get_localized_falls_back_to_prefix(tmp_path: Path) -> None:
    pt_dir = tmp_path / "pt"
    localized_path = pt_dir / "default.template.txt"
    _write_template(localized_path, "---\nid: default\nlocale: pt\n---\nPT body")
    registry = DeliveryTemplateRegistry(tmp_path)

    rendered = registry.render(None, {"transcript": "oi"}, language="pt-BR")

    assert "PT body" in rendered


def test_load_template_raises_for_missing_file(tmp_path: Path) -> None:
    registry = DeliveryTemplateRegistry(tmp_path)
    with pytest.raises(FileNotFoundError):
        registry._load_template(tmp_path / "absent.template.txt")  # type: ignore[attr-defined]
