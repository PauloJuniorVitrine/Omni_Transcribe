from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class DeliveryTemplate:
    """Represents a formatted template that can be applied to TXT outputs."""

    id: str
    name: str
    description: str
    body: str
    source_path: Path
    locale: Optional[str] = None


class DeliveryTemplateRegistry:
    """Loads and caches TXT templates with YAML front matter definitions."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._base_templates: Dict[str, DeliveryTemplate] = {}
        self._localized_templates: Dict[Tuple[str, str], DeliveryTemplate] = {}
        self._loaded_paths: Dict[str, DeliveryTemplate] = {}
        self._list_cache: List[DeliveryTemplate] | None = None
        self._load_all_templates()

    def list_templates(self) -> List[DeliveryTemplate]:
        if self._list_cache is not None:
            return list(self._list_cache)
        templates: Dict[str, DeliveryTemplate] = {}
        for template in self._base_templates.values():
            templates.setdefault(template.id, template)
        ordered = list(templates.values())
        self._list_cache = ordered
        return list(ordered)

    def get(self, template_id: Optional[str]) -> DeliveryTemplate:
        """Retorna o template lógico e carrega se necessário."""
        candidate = (template_id or self.default_template_id).strip()
        if not candidate:
            raise FileNotFoundError("Nenhum template definido.")
        if candidate not in self._base_templates:
            path = self.base_dir / f"{candidate}.template.txt"
            if path.exists():
                loaded_id = self._load_template(path)
                return self._base_templates[loaded_id]
            default = self._base_templates.get(self.default_template_id)
            if default:
                return default
            raise FileNotFoundError(f"Template '{candidate}' nao encontrado.")
        return self._base_templates[candidate]

    @property
    def default_template_id(self) -> str:
        if "default" in self._base_templates:
            return "default"
        if self._base_templates:
            return next(iter(self._base_templates))
        return "default"

    def render(self, template_id: Optional[str], context: Dict[str, str], language: Optional[str] = None) -> str:
        template = self._get_localized(template_id, language) if language else None
        if template is None:
            template = self.get(template_id)
        pattern = re.compile(r"{{\s*([\w\.]+)\s*}}")

        def replace(match: re.Match[str]) -> str:
            key = match.group(1)
            return context.get(key, "")

        rendered = pattern.sub(replace, template.body)
        return rendered.strip() + "\n"

    def _normalize_locale(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        normalized = value.strip().replace("_", "-").lower()
        return normalized or None

    def _load_template(self, path: Path) -> str:
        """
        Carrega um template e registra em _base_templates usando o ID lógico correto.
        Retorna o identificador utilizado.
        """
        if not path.exists():
            raise FileNotFoundError(f"Template nao encontrado: {path}")
        raw = path.read_text(encoding="utf-8")
        metadata, body = self._split_front_matter(raw)

        template_id = metadata.get("id")
        if not template_id:
            stem = path.stem
            if stem.endswith(".template"):
                stem = stem[: -len(".template")]
            template_id = stem

        template_id = str(template_id).strip()
        name = metadata.get("name") or template_id.title()
        description = metadata.get("description") or ""
        locale = self._normalize_locale(metadata.get("locale") or self._infer_locale_from_path(path))
        document = DeliveryTemplate(
            id=template_id,
            name=name,
            description=description,
            body=body.strip(),
            source_path=path,
            locale=locale,
        )
        resolved = str(path.resolve())
        self._loaded_paths[resolved] = document
        stem_id = path.stem.replace(".template", "").strip()
        if locale:
            self._localized_templates[(template_id, locale)] = document
            self._base_templates.setdefault(template_id, document)
            if stem_id:
                self._base_templates.setdefault(stem_id, document)
        else:
            self._base_templates[template_id] = document
            if stem_id:
                self._base_templates.setdefault(stem_id, document)
        self._invalidate_cache()
        return template_id

    def _load_all_templates(self) -> None:
        for path in sorted(self.base_dir.rglob("*.template.txt")):
            try:
                self._load_template(path)
            except FileNotFoundError:
                continue

    def _invalidate_cache(self) -> None:
        self._list_cache = None

    def _infer_locale_from_path(self, path: Path) -> Optional[str]:
        try:
            relative = path.relative_to(self.base_dir)
        except ValueError:
            return None
        parts = relative.parts
        if len(parts) > 1:
            return parts[0]
        return None

    def _get_localized(self, template_id: Optional[str], language: Optional[str]) -> Optional[DeliveryTemplate]:
        if not language:
            return None
        slug = template_id or self.default_template_id
        normalized_lang = self._normalize_locale(language)
        if not normalized_lang:
            return None
        key = (slug, normalized_lang)
        if key in self._localized_templates:
            return self._localized_templates[key]
        # Attempt to load localized files lazily.
        for path in self.base_dir.rglob(f"{slug}.template.txt"):
            resolved = str(path.resolve())
            if resolved not in self._loaded_paths:
                loaded_id = self._load_template(path)
                if (loaded_id, normalized_lang) in self._localized_templates:
                    return self._localized_templates[(loaded_id, normalized_lang)]
        if key in self._localized_templates:
            return self._localized_templates[key]
        prefix = normalized_lang.split("-")[0]
        if prefix and (slug, prefix) in self._localized_templates:
            return self._localized_templates[(slug, prefix)]
        return None

    @staticmethod
    def _split_front_matter(raw_text: str) -> tuple[Dict[str, str], str]:
        cleaned = raw_text.lstrip()
        if cleaned.startswith("---"):
            parts = cleaned.split("---", 2)
            if len(parts) >= 3:
                yaml_block, body = parts[1], parts[2]
                try:
                    import yaml
                except ModuleNotFoundError:  # pragma: no cover
                    return {}, body
                metadata = yaml.safe_load(yaml_block) or {}
                return metadata, body
        return {}, raw_text


__all__ = ["DeliveryTemplate", "DeliveryTemplateRegistry"]
