from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap_environment() -> None:
    """
    Prepare import paths so PyInstaller bundles can locate the application modules.
    """

    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"

    # We explicitly prepend both the project root and src/ so absolute imports like
    # `interfaces.cli.run_job` resolve even if the user runs the binary outside a venv.
    for candidate in (project_root, src_dir):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)

    # When the process spawns subprocesses (e.g., PyInstaller onefile), PYTHONPATH
    # might be empty. Defining it ensures that child interpreters inherit the same
    # search paths, preserving internal imports after packaging.
    if not os.environ.get("PYTHONPATH"):
        os.environ["PYTHONPATH"] = os.pathsep.join((str(project_root), str(src_dir)))


def main() -> None:
    """
    Entrypoint executed by both `python omni_cli_entry.py` and PyInstaller bundles.
    """

    _bootstrap_environment()

    # Import after bootstrapping so the interpreter sees the patched sys.path.
    from interfaces.cli.run_job import main as run_job_main

    # Running the existing CLI main keeps feature parity with scripts/run_job.py.
    run_job_main()


if __name__ == "__main__":
    main()
