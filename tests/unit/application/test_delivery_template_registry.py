from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from application.services.delivery_template_service import DeliveryTemplateRegistry, DeliveryTemplate


def _write_template(path: Path, metadata: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "---\n"
    payload += yaml.safe_dump(metadata).strip()
    payload += "\n---\n"
    payload += body
    path.write_text(payload, encoding="utf-8")


def test_get_returns_default_template_if_requested_missing(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    default_path = templates_dir / "default.template.txt"
    _write_template(default_path, {"id": "default", "name": "Default"}, "Olá {{name}}")

    registry = DeliveryTemplateRegistry(templates_dir)
    tmpl = registry.get("missing-profile")

    assert isinstance(tmpl, DeliveryTemplate)
    assert tmpl.id == "default"
    assert tmpl.body.startswith("Olá")


def test_render_prefers_localized_template_before_default(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    default_path = templates_dir / "default.template.txt"
    localized_dir = templates_dir / "pt-br"
    _write_template(default_path, {"id": "default"}, "Fallback {{value}}")
    localized_path = localized_dir / "default.template.txt"
    _write_template(localized_path, {"id": "default", "locale": "pt-br"}, "PT-BR {{value}}")

    registry = DeliveryTemplateRegistry(templates_dir)
    rendered = registry.render("default", {"value": "test"}, language="pt-BR")

    assert rendered.strip() == "PT-BR test"


def test_render_substitutes_missing_values_with_empty_string(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    default_path = templates_dir / "default.template.txt"
    _write_template(default_path, {"id": "default"}, "Texto {{missing}}")

    registry = DeliveryTemplateRegistry(templates_dir)
    output = registry.render(None, {}, language=None)

    assert "Tex" in output
    assert "{{" not in output


def test_list_templates_reuses_cached_documents(tmp_path: Path, monkeypatch) -> None:
    templates_dir = tmp_path / "templates"
    default_path = templates_dir / "default.template.txt"
    _write_template(default_path, {"id": "default"}, "Olá {{name}}")

    registry = DeliveryTemplateRegistry(templates_dir)
    load_calls: list[Path] = []
    original_loader = registry._load_template

    def tracked_loader(path: Path) -> str:
        load_calls.append(path)
        return original_loader(path)

    monkeypatch.setattr(registry, "_load_template", tracked_loader)

    assert len(registry.list_templates()) == 1
    assert len(registry.list_templates()) == 1
    assert len(load_calls) == 1


def test_get_missing_template_uses_default(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    default_path = templates_dir / "default.template.txt"
    _write_template(default_path, {"id": "default"}, "Fallback {{name}}")

    registry = DeliveryTemplateRegistry(templates_dir)
    fallback = registry.get("nonexistent")

    assert fallback.id == "default"
    assert "Fallback" in fallback.body


def test_get_none_template_id_returns_default(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    default_path = templates_dir / "default.template.txt"
    _write_template(default_path, {"id": "default"}, "Padrão {{name}}")

    registry = DeliveryTemplateRegistry(templates_dir)
    default_template = registry.get(None)

    assert default_template.id == "default"
    assert "Padrão" in default_template.body


def test_render_with_invalid_language_falls_back(tmp_path: Path) -> None:
    templates_dir = tmp_path / "templates"
    default_path = templates_dir / "default.template.txt"
    _write_template(default_path, {"id": "default"}, "Fallback texto")

    registry = DeliveryTemplateRegistry(templates_dir)
    rendered = registry.render("default", {}, language="   ")

    assert "Fallback" in rendered
    assert "{{" not in rendered


def test_get_raises_file_not_found_if_no_template_exists(tmp_path: Path) -> None:
    registry = DeliveryTemplateRegistry(tmp_path / "templates")
    with pytest.raises(FileNotFoundError):
        registry.get("any-template")
