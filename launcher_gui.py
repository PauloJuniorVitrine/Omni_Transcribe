from __future__ import annotations

import argparse
import contextlib
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn


def _bootstrap_paths() -> None:
    """
    Ensure project root and src are on sys.path so imports work in venv and frozen builds.
    """
    project_root = Path(__file__).resolve().parent
    src_dir = project_root / "src"
    for candidate in (project_root, src_dir):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)

    # Propagate PYTHONPATH to subprocesses (e.g., uvicorn reload or PyInstaller onefile)
    import os

    if not os.environ.get("PYTHONPATH"):
        os.environ["PYTHONPATH"] = os.pathsep.join((str(project_root), str(src_dir)))


def _find_available_port(host: str, preferred: int, span: int = 20) -> int:
    """
    Find an available port starting from `preferred`, scanning up to `preferred + span`.
    Defaults to the preferred port if it is free.
    """
    for port in range(preferred, preferred + span + 1):
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex((host, port)) != 0:
                return port
    return preferred


def _open_browser_later(url: str, delay: float = 1.0) -> None:
    def _open() -> None:
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open, daemon=True).start()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch TranscribeFlow GUI (FastAPI + web dashboard).")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the HTTP server (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000).")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically.")
    parser.add_argument("--reload", action="store_true", help="Enable autoreload (for local development).")
    return parser.parse_args()


def main() -> None:
    _bootstrap_paths()
    args = parse_args()

    # Import after sys.path bootstrap so modules resolve.
    import interfaces.http.app  # noqa: WPS433  # type: ignore

    host = args.host
    port = _find_available_port(host, args.port)
    app_path = "interfaces.http.app:app"
    config = uvicorn.Config(
        app_path,
        host=host,
        port=port,
        reload=args.reload,
        log_level="info",
    )
    server = uvicorn.Server(config)

    if not args.no_browser:
        _open_browser_later(f"http://{host}:{port}")

    server.run()


if __name__ == "__main__":
    main()
