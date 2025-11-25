from __future__ import annotations

from pathlib import Path

from application.services.delivery_template_service import DeliveryTemplateRegistry


def _write_template(path: Path, template_id: str, body: str, locale: str | None = None) -> None:
    lines = ["---", f"id: {template_id}", "name: Test Template", "description: Desc"]
    if locale:
        lines.append(f"locale: {locale}")
    lines.extend(["---", body])
    path.write_text("\n".join(lines), encoding="utf-8")


def test_list_and_render_templates(tmp_path):
    templates_dir = tmp_path / "profiles" / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    default = templates_dir / "default.template.txt"
    _write_template(default, "default", "{{greeting}} {{name}}")

    registry = DeliveryTemplateRegistry(templates_dir)
    templates = registry.list_templates()
    assert any(template.id == "default" for template in templates)

    rendered = registry.render("default", {"greeting": "Oi", "name": "Ana"})
    assert "Oi Ana" in rendered


def test_localized_template_selection(tmp_path):
    templates_dir = tmp_path / "profiles" / "templates"
    localized_dir = templates_dir / "pt-br"
    localized_dir.mkdir(parents=True, exist_ok=True)
    default = templates_dir / "default.template.txt"
    localized = localized_dir / "default.template.txt"
    _write_template(default, "default", "Default {{name}}")
    _write_template(localized, "default", "Local {{name}}", locale="pt-br")

    registry = DeliveryTemplateRegistry(templates_dir)
    rendered_default = registry.render("default", {"name": "Ana"})
    assert "Default" in rendered_default
    rendered_localized = registry.render("default", {"name": "Ana"}, language="pt-BR")
    assert "Local" in rendered_localized


def test_get_localized_reads_fallback_locale(tmp_path):
    templates_dir = tmp_path / "profiles" / "templates"
    lang_dir = templates_dir / "en-us"
    lang_dir.mkdir(parents=True, exist_ok=True)
    default = templates_dir / "default.template.txt"
    en_default = lang_dir / "default.template.txt"
    _write_template(default, "default", "Default")
    _write_template(en_default, "default", "EN Default", locale="en-us")

    registry = DeliveryTemplateRegistry(templates_dir)
    result = registry.render("default", {}, language="en-US")
    assert "EN Default" in result
