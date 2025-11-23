from __future__ import annotations

import json
from pathlib import Path

from config.feature_flags import FeatureFlagProvider


def test_default_flags_include_download_signature(tmp_path: Path):
    provider = FeatureFlagProvider(path=tmp_path / "flags.json")
    flags = provider.snapshot()
    assert flags["downloads.signature_required"] is True


def test_snapshot_merges_overrides(tmp_path: Path):
    path = tmp_path / "flags.json"
    path.write_text(json.dumps({"downloads.signature_required": False}), encoding="utf-8")
    provider = FeatureFlagProvider(path=path)
    flags = provider.snapshot()
    assert flags["downloads.signature_required"] is False
    assert flags["dashboard.live_summary"] is True
