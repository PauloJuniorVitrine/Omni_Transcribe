from __future__ import annotations

from application.services.subtitle_formatter import SubtitleFormatter
from domain.entities.profile import Profile
from domain.entities.transcription import Segment


def test_wrap_text_truncates_excess_lines() -> None:
    formatter = SubtitleFormatter()
    profile = Profile(
        id="p",
        meta={"subtitle": {"max_chars_per_line": 5, "max_lines": 2}},
        prompt_body="",
    )
    segments = [Segment(id=1, start=0.0, end=1.0, text="abcdef ghijkl", speaker=None)]

    output = formatter.to_srt(segments, profile)

    # ensure at most 2 lines and truncated width
    lines = [line for line in output.splitlines() if line and not line.isdigit() and "-->" not in line]
    assert len(lines) <= 2
    assert all(len(line) <= 5 for line in lines)
