from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SubtitleConfig:
    max_chars_per_line: int
    max_lines: int
    reading_speed_cps: int


@dataclass
class Profile:
    """Editorial profile loaded from .prompt.txt definitions."""

    id: str
    meta: Dict[str, Any]
    prompt_body: str
    source_path: Optional[str] = None
    version: str = "v1"
    disclaimers: List[str] = field(default_factory=list)

    def subtitle_rules(self) -> SubtitleConfig:
        subtitle_meta = self.meta.get("subtitle", {})
        return SubtitleConfig(
            max_chars_per_line=int(subtitle_meta.get("max_chars_per_line", 42)),
            max_lines=int(subtitle_meta.get("max_lines", 2)),
            reading_speed_cps=int(subtitle_meta.get("reading_speed_cps", 17)),
        )

    def requires_translation(self) -> bool:
        instructions = self.meta.get("instructions") or []
        language = self.meta.get("language", "auto")
        return "translate" in instructions or language not in ("auto", "", None)

    def should_anonymize_pii(self) -> bool:
        post_edit = self.meta.get("post_edit", {})
        return bool(post_edit.get("anonymize_pii", False))
