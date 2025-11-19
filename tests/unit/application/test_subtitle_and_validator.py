from __future__ import annotations

from domain.entities.profile import Profile
from domain.entities.transcription import Segment
from application.services.subtitle_formatter import SubtitleFormatter
from application.services.validator_service import TranscriptValidator


def make_profile() -> Profile:
    return Profile(
        id="geral",
        meta={
            "subtitle": {
                "max_chars_per_line": 12,
                "max_lines": 2,
                "reading_speed_cps": 10,
            }
        },
        prompt_body="body",
    )


def test_subtitle_formatter_wraps_text_into_allowed_lines() -> None:
    formatter = SubtitleFormatter()
    profile = make_profile()
    segments = [Segment(id=1, start=0.0, end=2.0, text="This subtitle line should wrap nicely")]

    srt = formatter.to_srt(segments, profile)
    assert "1" in srt.splitlines()[0]
    lines = [line for line in srt.splitlines() if line and "-->" not in line and not line.isdigit()]
    assert all(len(line) <= 12 for line in lines)
    assert len(lines) <= 2

    vtt = formatter.to_vtt(segments, profile)
    assert vtt.startswith("WEBVTT")


def test_transcript_validator_flags_long_lines_and_speed() -> None:
    validator = TranscriptValidator()
    profile = make_profile()
    segments = [
        Segment(id=1, start=0.0, end=0.5, text="This line is definitely too long"),
    ]

    warnings = validator.validate(profile, segments)

    assert any("cps" in warning.lower() or "cps" in warning for warning in warnings)
    assert any("caracteres" in warning.lower() or "caracteres" in warning.lower() for warning in warnings)
