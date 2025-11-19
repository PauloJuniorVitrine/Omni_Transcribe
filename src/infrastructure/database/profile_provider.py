from __future__ import annotations

from pathlib import Path

from domain.entities.profile import Profile
from domain.ports.repositories import ProfileProvider

from config import profile_loader


class FilesystemProfileProvider(ProfileProvider):
    """Loads profiles from .prompt.txt definitions located in profiles/."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir

    def get(self, profile_id: str) -> Profile:
        document = profile_loader.load_profile(profile_id, self.base_dir)
        meta = document.meta
        disclaimers = meta.get("disclaimers", [])
        return Profile(
            id=document.profile_id,
            meta=meta,
            prompt_body=document.prompt_body,
            source_path=str(document.source_path),
            disclaimers=disclaimers,
        )
