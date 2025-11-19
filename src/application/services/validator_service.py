from __future__ import annotations

from typing import List

from domain.entities.profile import Profile
from domain.entities.transcription import Segment


class TranscriptValidator:
    """Validates transcript segments against subtitle constraints."""

    def validate(self, profile: Profile, segments: List[Segment]) -> List[str]:
        rules = profile.subtitle_rules()
        warnings: List[str] = []
        for segment in segments:
            duration = max(segment.end - segment.start, 0.1)
            cps = len(segment.text) / duration
            if cps > rules.reading_speed_cps:
                warnings.append(f"Segmento {segment.id} ultrapassa CPS ({cps:.2f} > {rules.reading_speed_cps})")
            for line in segment.text.split("\n"):
                if len(line) > rules.max_chars_per_line:
                    warnings.append(
                        f"Segmento {segment.id} excede caracteres por linha ({len(line)} > {rules.max_chars_per_line})"
                    )
        return warnings
