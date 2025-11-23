from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict

DEFAULT_FEATURE_FLAGS: Dict[str, bool] = {
    "dashboard.live_summary": True,
    "dashboard.live_incidents": True,
    "jobs.manual_reprocess": True,
    "ui.api_settings": True,
    "downloads.signature_required": True,
}


@dataclass
class FeatureFlagProvider:
    path: Path = field(default_factory=lambda: Path("config/feature_flags.json"))

    def __post_init__(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(DEFAULT_FEATURE_FLAGS)

    def snapshot(self) -> Dict[str, bool]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Feature flags must be a dict.")
        except (OSError, ValueError, json.JSONDecodeError):
            data = {}
        merged = {**DEFAULT_FEATURE_FLAGS, **{k: bool(v) for k, v in data.items()}}
        return merged

    def is_enabled(self, name: str, default: bool | None = None) -> bool:
        flags = self.snapshot()
        if name in flags:
            return flags[name]
        return DEFAULT_FEATURE_FLAGS.get(name, default if default is not None else False)

    def set_flag(self, name: str, value: bool) -> None:
        flags = self.snapshot()
        flags[name] = bool(value)
        self._write(flags)

    def _write(self, data: Dict[str, bool]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


__all__ = ["FeatureFlagProvider", "DEFAULT_FEATURE_FLAGS"]
