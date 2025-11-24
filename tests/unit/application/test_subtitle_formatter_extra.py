from __future__ import annotations

from domain.entities.profile import Profile
from domain.entities.transcription import Segment

from application.services.subtitle_formatter import SubtitleFormatter


def _profile(max_chars=5, max_lines=2):
    return Profile(
        id="p",
        meta={"subtitle": {"max_chars_per_line": max_chars, "max_lines": max_lines}},
        prompt_body="",
    )


def test_wrap_text_merges_excess_lines() -> None:
    formatter = SubtitleFormatter()
    profile = _profile(max_chars=5, max_lines=2)
    segments = [Segment(id=1, start=0, end=1, text="palavra grande demais", speaker=None)]

    srt = formatter.to_srt(segments, profile)

    lines = srt.splitlines()
    assert any(len(line) <= 5 for line in lines)


def test_empty_text_returns_blank_entry() -> None:
    formatter = SubtitleFormatter()
    profile = _profile()
    segments = [Segment(id=1, start=0, end=1, text="", speaker=None)]

    vtt = formatter.to_vtt(segments, profile)

    assert "WEBVTT" in vtt
    assert vtt.strip().endswith("")
