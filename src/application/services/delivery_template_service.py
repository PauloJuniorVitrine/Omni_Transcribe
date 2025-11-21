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

    def list_templates(self) -> List[DeliveryTemplate]:
        if self._list_cache is not None:
            return list(self._list_cache)
        templates: List[DeliveryTemplate] = []
        for path in sorted(self.base_dir.rglob("*.template.txt")):
            resolved = str(path.resolve())
            document = self._loaded_paths.get(resolved)
            if not document:
                document = self._load_template(path)
            templates.append(document)
        self._list_cache = templates
        return list(templates)

    def get(self, template_id: Optional[str]) -> DeliveryTemplate:
        candidate = template_id or self.default_template_id
        if candidate not in self._base_templates:
            path = self.base_dir / f"{candidate}.template.txt"
            if not path.exists():
                path = self.base_dir / f"{self.default_template_id}.template.txt"
            self._load_template(path)
        return self._base_templates[candidate]

    @property
    def default_template_id(self) -> str:
        default_path = self.base_dir / "default.template.txt"
        if default_path.exists():
            return "default"
        for path in self.base_dir.glob("*.template.txt"):
            return path.stem.replace(".template", "")
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

    def _load_template(self, path: Path) -> DeliveryTemplate:
        if not path.exists():
            raise FileNotFoundError(f"Template nao encontrado: {path}")
        raw = path.read_text(encoding="utf-8")
        metadata, body = self._split_front_matter(raw)
        template_id = metadata.get("id") or path.stem.replace(".template", "")
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
        if locale:
            self._localized_templates[(template_id, locale)] = document
            # Guarantee that callers relying on `.get(id)` can resolve at least one variant.
            self._base_templates.setdefault(template_id, document)
        else:
            self._base_templates[template_id] = document
        self._invalidate_cache()
        return document

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
                self._load_template(path)
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
