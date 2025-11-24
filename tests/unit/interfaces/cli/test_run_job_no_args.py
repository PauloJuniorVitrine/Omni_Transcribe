from __future__ import annotations

import pytest

from interfaces.cli import run_job


def test_run_job_exits_when_missing_arguments(monkeypatch):
    class _Container:
        def __init__(self):
            self.job_repository = None
            self.create_job_use_case = None
            self.pipeline_use_case = None
            self.retry_use_case = None

    monkeypatch.setattr(run_job, "get_container", lambda: _Container())
    monkeypatch.setattr("sys.argv", ["run_job"])
    with pytest.raises(SystemExit):
        run_job.main()
