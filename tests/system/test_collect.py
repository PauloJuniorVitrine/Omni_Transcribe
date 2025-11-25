from __future__ import annotations

import pytest


def test_pytest_collected_tests(pytestconfig: pytest.Config):
    """Fail fast if pytest collects zero tests (CI guard)."""
    collected = getattr(pytestconfig.session, "testscollected", None)
    if collected is None:
        pytest.skip("pytest collection metadata unavailable")
    assert collected > 0, "Pytest collected zero tests; ensure suite is discovered"
