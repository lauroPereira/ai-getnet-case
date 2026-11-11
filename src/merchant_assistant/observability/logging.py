"""JSON log lines on stdout (one object per line), suitable for container log collection."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "pid": record.process,  # which API worker wrote the line (v0.13.0: several workers)
            "msg": record.getMessage(),
        }
        event = getattr(record, "event", None)
        if isinstance(event, dict):
            payload.update(event)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


AUTHORIZE_PATH = "/v1/auth/authorize"


class AuthorizeQueryFilter(logging.Filter):
    """The access line of `/v1/auth/authorize` keeps the path and drops the query, which carries `state` and
    `code_challenge` (uvicorn logs `client - "METHOD path?query HTTP/x" status`, the path as the third argument)."""

    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str):
            path, _, query = args[2].partition("?")
            if query and path.endswith(AUTHORIZE_PATH):
                record.args = (*args[:2], path, *args[3:])
        return True


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("merchant_assistant")
    root.handlers = [handler]
    root.setLevel(level.upper())
    root.propagate = False
    access = logging.getLogger("uvicorn.access")  # the factory runs in each worker, after uvicorn set up its logging
    if not any(isinstance(f, AuthorizeQueryFilter) for f in access.filters):
        access.addFilter(AuthorizeQueryFilter())
