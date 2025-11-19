from __future__ import annotations

import textwrap
from typing import Iterable, List

from domain.entities.profile import Profile
from domain.entities.transcription import Segment


class SubtitleFormatter:
    """Builds subtitle strings (SRT/VTT) applying profile constraints."""

    def __init__(self, newline: str = "\n") -> None:
        self.newline = newline

    def to_srt(self, segments: Iterable[Segment], profile: Profile) -> str:
        entries = self._build_entries(list(segments), profile)
        blocks: List[str] = []
        for idx, entry in enumerate(entries, start=1):
            blocks.append(f"{idx}")
            blocks.append(f"{self._format_timestamp(entry.start)} --> {self._format_timestamp(entry.end)}")
            blocks.extend(entry.lines)
            blocks.append("")  # blank line
        return self.newline.join(blocks).strip() + self.newline

    def to_vtt(self, segments: Iterable[Segment], profile: Profile) -> str:
        entries = self._build_entries(list(segments), profile)
        blocks: List[str] = ["WEBVTT", ""]
        for entry in entries:
            blocks.append(f"{self._format_timestamp(entry.start)} --> {self._format_timestamp(entry.end)}")
            blocks.extend(entry.lines)
            blocks.append("")
        return self.newline.join(blocks).strip() + self.newline

    def _build_entries(self, segments: List[Segment], profile: Profile) -> List["SubtitleEntry"]:
        rules = profile.subtitle_rules()
        entries: List[SubtitleEntry] = []
        for segment in segments:
            wrapped = self._wrap_text(segment.text, rules.max_chars_per_line, rules.max_lines)
            entries.append(SubtitleEntry(start=segment.start, end=segment.end, lines=wrapped))
        return entries

    def _wrap_text(self, text: str, max_chars: int, max_lines: int) -> List[str]:
        wrapped = textwrap.wrap(text, width=max_chars)
        if not wrapped:
            return [""]
        if len(wrapped) <= max_lines:
            return wrapped
        # Merge extra lines respecting total lines permitted.
        merged = wrapped[: max_lines - 1]
        remaining = " ".join(wrapped[max_lines - 1 :])
        merged.append(remaining[: max_chars])
        return merged

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        millis = int(round(seconds * 1000))
        hours = millis // 3_600_000
        millis -= hours * 3_600_000
        minutes = millis // 60_000
        millis -= minutes * 60_000
        secs = millis // 1000
        millis -= secs * 1000
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


class SubtitleEntry:
    def __init__(self, start: float, end: float, lines: List[str]) -> None:
        self.start = start
        self.end = end
        self.lines = lines
