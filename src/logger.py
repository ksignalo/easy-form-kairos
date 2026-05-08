"""
Structured logger — every run carries a requestId for full traceability.
Logs are written to stdout as structured key=value lines so they can be
ingested by any log aggregator without extra dependencies.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(message)s"
logging.basicConfig(format=_LOG_FORMAT, datefmt="%Y-%m-%dT%H:%M:%S")

_root = logging.getLogger("easeofdoing")
_root.setLevel(logging.INFO)


def _fmt(fields: dict[str, Any]) -> str:
    return " ".join(f"{k}={v!r}" for k, v in fields.items())


class RunLogger:
    """Per-invocation logger that attaches a stable requestId to every line."""

    def __init__(self, request_id: str | None = None) -> None:
        self.request_id: str = request_id or str(uuid.uuid4())[:8]

    def _emit(self, level: int, event: str, **fields: Any) -> None:
        msg = _fmt({"requestId": self.request_id, "event": event, **fields})
        _root.log(level, msg)

    def info(self, event: str, **fields: Any) -> None:
        self._emit(logging.INFO, event, **fields)

    def warning(self, event: str, **fields: Any) -> None:
        self._emit(logging.WARNING, event, **fields)

    def error(self, event: str, **fields: Any) -> None:
        self._emit(logging.ERROR, event, **fields)

    def debug(self, event: str, **fields: Any) -> None:
        self._emit(logging.DEBUG, event, **fields)
