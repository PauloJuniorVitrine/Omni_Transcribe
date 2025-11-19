from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml


class ProfileLoaderError(Exception):
    """Raised when a profile file cannot be parsed or located."""


@dataclass(frozen=True)
class ProfileDocument:
    """Represents a parsed profile specification (front matter + prompt body)."""

    profile_id: str
    meta: Dict[str, Any]
    prompt_body: str
    source_path: Path

    def dump_meta(self) -> str:
        """Return the meta section as a pretty-printed JSON string."""
        return json.dumps(self.meta, ensure_ascii=False, indent=2)


def _split_front_matter(raw_text: str) -> Tuple[str, str]:
    """
    Split a .prompt.txt into YAML front matter and body text.
    Expected format:
    ---
    <yaml>
    ---
    <prompt body>
    """
    cleaned = raw_text.lstrip()
    if not cleaned.startswith("---"):
        raise ProfileLoaderError("Perfil inválido: front matter YAML ausente.")

    parts = cleaned.split("---", 2)
    if len(parts) < 3:
        raise ProfileLoaderError("Perfil inválido: bloco YAML não fechado corretamente.")
    _, yaml_block, body = parts
    return yaml_block.strip(), body.strip()


def parse_profile_file(path: Path) -> ProfileDocument:
    """Parse a profile file and return a ProfileDocument."""
    if not path.exists():
        raise ProfileLoaderError(f"Perfil não encontrado: {path}")

    raw_text = path.read_text(encoding="utf-8")
    yaml_block, body = _split_front_matter(raw_text)
    meta: Dict[str, Any] = yaml.safe_load(yaml_block) or {}
    profile_id = meta.get("id") or path.stem.replace(".prompt", "")

    if not profile_id:
        raise ProfileLoaderError(f"Perfil {path} precisa definir um identificador.")

    return ProfileDocument(profile_id=profile_id, meta=meta, prompt_body=body, source_path=path)


def load_profile(profile_name: str, profiles_dir: Path) -> ProfileDocument:
    """
    Load a profile by convention (<profile>.prompt.txt) from the profiles directory.
    """
    filename = f"{profile_name}.prompt.txt"
    target = profiles_dir / filename
    return parse_profile_file(target)


def resolve_profile_by_path(source_path: Path, profiles_dir: Path, default_profile: str = "geral") -> ProfileDocument:
    """
    Infer which profile to use based on the relative path of the audio inside inbox/.
    Subfolders like inbox/medico/file.wav -> profile 'medico'.
    """
    relative_parent = source_path.parent.name.lower()
    candidate = relative_parent if relative_parent else default_profile
    try:
        return load_profile(candidate, profiles_dir)
    except ProfileLoaderError:
        # Fallback to default profile when subfolder profile is missing.
        return load_profile(default_profile, profiles_dir)
