from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List

from filelock import FileLock


def _lock_for(path: Path) -> FileLock:
    return FileLock(str(path) + ".lock")


def read_json_list(path: Path) -> List[Any]:
    lock = _lock_for(path)
    with lock:
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8")
        return json.loads(text) if text.strip() else []


def write_json_list(path: Path, data: List[Any]) -> None:
    lock = _lock_for(path)
    with lock:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
