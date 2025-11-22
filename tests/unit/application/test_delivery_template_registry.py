from __future__ import annotations

from pathlib import Path

from application.services.delivery_template_service import DeliveryTemplateRegistry


def _write_template(path: Path, metadata: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{metadata.strip()}\n---\n{body.strip()}\n", encoding="utf-8")


def test_registry_renders_default_and_localized(tmp_path):
    default_path = tmp_path / "default.template.txt"
    _write_template(default_path, "id: default\nname: Default\ndescription: Base", "Hello {{job_id}}")

    localized_path = tmp_path / "pt-br" / "default.template.txt"
    # locale inferred from folder name when metadata lacks explicit locale
    _write_template(localized_path, "name: Local PT\n", "Ola {{language}}")

    registry = DeliveryTemplateRegistry(tmp_path)

    rendered_default = registry.render("default", {"job_id": "abc", "transcript": "t"}, language=None)
    assert rendered_default.startswith("Hello abc")

    rendered_localized = registry.render("default", {"job_id": "abc", "language": "pt-BR"}, language="pt-BR")
    assert rendered_localized.startswith("Ola pt-BR")

    templates = registry.list_templates()
    assert len(templates) >= 2
    # cache reuse
    again = registry.list_templates()
    assert len(again) == len(templates)
