from __future__ import annotations

import pytest

from interfaces.cli import run_job


def test_run_job_exits_when_missing_arguments(monkeypatch):
    monkeypatch.setattr("sys.argv", ["run_job"])
    with pytest.raises(SystemExit):
        run_job.main()
