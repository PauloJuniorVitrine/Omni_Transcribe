from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

_configured = False


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        payload: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> logging.Logger:
    global _configured
    logger = logging.getLogger("transcribeflow")
    # Always honor requested level, but avoid duplicating handlers.
    logger.setLevel(level)
    root = logging.getLogger()
    root.setLevel(level)

    if not _configured:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonLogFormatter())
        logger.addHandler(handler)
        logger.propagate = False
        _configured = True
    return logger
