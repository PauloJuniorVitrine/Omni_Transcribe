from __future__ import annotations

import sys
from pathlib import Path
import types


def pytest_configure() -> None:
    """Ensure src/ is available on PYTHONPATH for absolute imports."""
    root = Path(__file__).resolve().parents[1]
    src = root / "src"
    for path in (str(root), str(src)):
        if path not in sys.path:
            sys.path.insert(0, path)

    try:
        import pydantic_settings  # type: ignore  # noqa: F401
    except ImportError:
        stub = types.ModuleType("pydantic_settings")

        class BaseSettings:  # minimal stub for tests
            pass

        class SettingsConfigDict(dict):
            pass

        stub.BaseSettings = BaseSettings
        stub.SettingsConfigDict = SettingsConfigDict
        sys.modules["pydantic_settings"] = stub

    try:
        import python_multipart  # type: ignore  # noqa: F401
    except ImportError:
        py_multipart_stub = types.ModuleType("python_multipart")
        py_multipart_stub.__version__ = "0.1.0"
        sys.modules["python_multipart"] = py_multipart_stub
